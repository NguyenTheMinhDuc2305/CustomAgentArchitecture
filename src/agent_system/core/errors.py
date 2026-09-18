from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AgentFailureKind(StrEnum):
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    POLICY = "policy"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"
    EXECUTION = "execution"
    INTERNAL = "internal"


@dataclass(frozen=True, slots=True)
class AgentFailure:
    kind: AgentFailureKind
    message: str
    retryable: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("Failure message cannot be blank")


class AgentSystemError(Exception):
    """Base exception for expected agent-system errors."""

    failure_kind = AgentFailureKind.INTERNAL
    retryable = False

    def to_failure(self) -> AgentFailure:
        return AgentFailure(
            kind=self.failure_kind,
            message=str(self),
            retryable=self.retryable,
        )


class AgentValidationError(AgentSystemError):
    failure_kind = AgentFailureKind.VALIDATION


class AgentConfigurationError(AgentSystemError):
    failure_kind = AgentFailureKind.CONFIGURATION


class AgentPolicyError(AgentSystemError):
    failure_kind = AgentFailureKind.POLICY


class AgentExecutionError(AgentSystemError):
    failure_kind = AgentFailureKind.EXECUTION


class AgentInterruptedError(AgentSystemError):
    failure_kind = AgentFailureKind.INTERRUPTED
    retryable = True


class AgentNotFoundError(AgentConfigurationError):
    pass