import pytest

from agent_system.core.errors import (
    AgentFailure,
    AgentFailureKind,
    AgentInterruptedError,
    AgentNotFoundError,
)


def test_converts_exception_to_failure() -> None:
    error = AgentNotFoundError(
        "Agent not found: planner"
    )

    failure = error.to_failure()

    assert failure.kind is AgentFailureKind.CONFIGURATION
    assert failure.message == "Agent not found: planner"
    assert failure.retryable is False


def test_interrupted_error_is_retryable() -> None:
    failure = AgentInterruptedError(
        "Runtime stopped unexpectedly"
    ).to_failure()

    assert failure.kind is AgentFailureKind.INTERRUPTED
    assert failure.retryable is True


@pytest.mark.parametrize("message", ["", " ", "   "])
def test_failure_rejects_blank_message(
    message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="message cannot be blank",
    ):
        AgentFailure(
            kind=AgentFailureKind.INTERNAL,
            message=message,
        )