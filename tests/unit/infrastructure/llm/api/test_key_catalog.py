from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from agent_system.infrastructure.llm.api.key_catalog import (
    ApiKeyCatalog,
    ApiKeyCatalogError,
)


def write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_loads_normalizes_and_orders_candidates(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "api_keys.csv",
        "key,provider,model,enabled,priority\n"
        "secret-low, OpenAI ,model-a,true,20\n"
        "secret-high,openai,model-a,yes,10\n"
        "secret-disabled,openai,model-a,false,1\n",
    )

    catalog = ApiKeyCatalog.from_csv(path)
    candidates = catalog.candidates(" OPENAI ", "model-a")

    assert [item.api_key for item in candidates] == [
        "secret-high",
        "secret-low",
    ]
    assert all(item.provider == "openai" for item in candidates)


def test_safe_outputs_do_not_reveal_keys(tmp_path: Path) -> None:
    secret = "must-not-appear"
    path = write_csv(
        tmp_path / "api_keys.csv",
        f"key,provider,model\n{secret},provider-a,model-a\n",
    )

    catalog = ApiKeyCatalog.from_csv(path)
    credential = catalog.credentials()[0]
    safe_frame = catalog.safe_frame()

    assert secret not in repr(credential)
    assert "key" not in safe_frame.columns
    assert secret not in safe_frame.to_string()


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("provider,model\nprovider-a,model-a\n", "missing required columns"),
        ("key,provider,model\n,provider-a,model-a\n", "blank required fields"),
        (
            "key,provider,model,enabled\nsecret,provider-a,model-a,perhaps\n",
            "invalid enabled values",
        ),
        (
            "key,provider,model,priority\nsecret,provider-a,model-a,-1\n",
            "invalid priority values",
        ),
        (
            "key,provider,model\n"
            "secret,provider-a,model-a\n"
            "secret,provider-a,model-a\n",
            "duplicate routes",
        ),
    ],
)
def test_rejects_invalid_catalogs(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    path = write_csv(tmp_path / "api_keys.csv", content)

    with pytest.raises(ApiKeyCatalogError, match=message):
        ApiKeyCatalog.from_csv(path)


def test_accepts_an_empty_catalog_with_a_valid_header(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "api_keys.csv",
        "key,provider,model,enabled,priority\n",
    )

    catalog = ApiKeyCatalog.from_csv(path)

    assert catalog.credentials() == ()
    assert isinstance(catalog.safe_frame(), pd.DataFrame)
