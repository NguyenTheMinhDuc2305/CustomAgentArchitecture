"""Validated, secret-safe access to the local API credential CSV."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = frozenset({"key", "provider", "model"})
OPTIONAL_COLUMNS = frozenset({"enabled", "priority"})
ALLOWED_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS

TRUE_VALUES = frozenset({"true", "1", "yes"})
FALSE_VALUES = frozenset({"false", "0", "no"})


class ApiKeyCatalogError(ValueError):
    """Raised when the credential CSV is missing or invalid."""


@dataclass(frozen=True, slots=True)
class ApiCredential:
    """One provider/model route backed by an API key.

    The secret is deliberately excluded from ``repr`` so routine diagnostics
    cannot print it accidentally.
    """

    key_id: str
    provider: str
    model: str
    api_key: str = field(repr=False)
    enabled: bool = True
    priority: int = 100


class ApiKeyCatalog:
    """Load and query API credentials through a normalized DataFrame."""

    def __init__(self, frame: pd.DataFrame) -> None:
        self._frame = self._normalize(frame)

    @classmethod
    def from_csv(cls, path: str | Path) -> "ApiKeyCatalog":
        csv_path = Path(path)

        if not csv_path.is_file():
            raise ApiKeyCatalogError(
                f"API credential CSV does not exist: {csv_path}"
            )

        try:
            frame = pd.read_csv(
                csv_path,
                dtype=str,
                keep_default_na=False,
            )
        except pd.errors.EmptyDataError as exc:
            raise ApiKeyCatalogError(
                f"API credential CSV has no header: {csv_path}"
            ) from exc
        except (OSError, pd.errors.ParserError) as exc:
            raise ApiKeyCatalogError(
                f"Unable to read API credential CSV: {csv_path}"
            ) from exc

        return cls(frame)

    def credentials(self) -> tuple[ApiCredential, ...]:
        return tuple(
            ApiCredential(
                key_id=row.key_id,
                provider=row.provider,
                model=row.model,
                api_key=row.key,
                enabled=bool(row.enabled),
                priority=int(row.priority),
            )
            for row in self._frame.itertuples(index=False)
        )

    def candidates(
        self,
        provider: str,
        model: str,
    ) -> tuple[ApiCredential, ...]:
        normalized_provider = provider.strip().lower()
        normalized_model = model.strip()

        selected = self._frame[
            self._frame["enabled"]
            & (self._frame["provider"] == normalized_provider)
            & (self._frame["model"] == normalized_model)
        ].sort_values(["priority", "key_id"], kind="stable")

        return tuple(
            ApiCredential(
                key_id=row.key_id,
                provider=row.provider,
                model=row.model,
                api_key=row.key,
                enabled=bool(row.enabled),
                priority=int(row.priority),
            )
            for row in selected.itertuples(index=False)
        )

    def safe_frame(self) -> pd.DataFrame:
        """Return diagnostics without a raw or partially revealed key."""

        return self._frame[
            ["key_id", "provider", "model", "enabled", "priority"]
        ].copy(deep=True)

    @classmethod
    def _normalize(cls, source: pd.DataFrame) -> pd.DataFrame:
        frame = source.copy(deep=True)
        normalized_columns = [str(column).strip() for column in frame.columns]

        if len(normalized_columns) != len(set(normalized_columns)):
            raise ApiKeyCatalogError("API credential CSV has duplicate columns")

        frame.columns = normalized_columns

        missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
        if missing:
            raise ApiKeyCatalogError(
                "API credential CSV is missing required columns: "
                + ", ".join(missing)
            )

        unknown = sorted(set(frame.columns) - ALLOWED_COLUMNS)
        if unknown:
            raise ApiKeyCatalogError(
                "API credential CSV has unknown columns: "
                + ", ".join(unknown)
            )

        for column in REQUIRED_COLUMNS:
            frame[column] = frame[column].astype("string").str.strip()

        blank_rows = frame[list(REQUIRED_COLUMNS)].eq("").any(axis=1)
        if blank_rows.any():
            rows = ", ".join(str(index + 2) for index in frame.index[blank_rows])
            raise ApiKeyCatalogError(
                f"API credential CSV has blank required fields on rows: {rows}"
            )

        frame["provider"] = frame["provider"].str.lower()

        if "enabled" not in frame:
            frame["enabled"] = True
        else:
            enabled = frame["enabled"].astype("string").str.strip().str.lower()
            enabled = enabled.replace("", "true")
            invalid_enabled = ~enabled.isin(TRUE_VALUES | FALSE_VALUES)

            if invalid_enabled.any():
                rows = ", ".join(
                    str(index + 2) for index in frame.index[invalid_enabled]
                )
                raise ApiKeyCatalogError(
                    f"API credential CSV has invalid enabled values on rows: {rows}"
                )

            frame["enabled"] = enabled.isin(TRUE_VALUES)

        if "priority" not in frame:
            frame["priority"] = 100
        else:
            priority = frame["priority"].astype("string").str.strip()
            priority = priority.replace("", "100")
            numeric_priority = pd.to_numeric(priority, errors="coerce")
            invalid_priority = (
                numeric_priority.isna()
                | (numeric_priority < 0)
                | (numeric_priority % 1 != 0)
            )

            if invalid_priority.any():
                rows = ", ".join(
                    str(index + 2) for index in frame.index[invalid_priority]
                )
                raise ApiKeyCatalogError(
                    f"API credential CSV has invalid priority values on rows: {rows}"
                )

            frame["priority"] = numeric_priority.astype(int)

        duplicate_rows = frame.duplicated(
            subset=["key", "provider", "model"],
            keep=False,
        )
        if duplicate_rows.any():
            rows = ", ".join(
                str(index + 2) for index in frame.index[duplicate_rows]
            )
            raise ApiKeyCatalogError(
                f"API credential CSV has duplicate routes on rows: {rows}"
            )

        frame["key_id"] = [
            cls._fingerprint(provider, key)
            for provider, key in zip(
                frame["provider"],
                frame["key"],
                strict=True,
            )
        ]

        return frame[
            ["key_id", "key", "provider", "model", "enabled", "priority"]
        ].reset_index(drop=True)

    @staticmethod
    def _fingerprint(provider: str, api_key: str) -> str:
        digest = sha256(f"{provider}\0{api_key}".encode()).hexdigest()
        return f"{provider}:{digest[:12]}"
