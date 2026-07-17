"""Errors surfaced by the deterministic agent core."""


class AgentError(RuntimeError):
    """Base class for controlled run failures."""


class ModelProtocolError(AgentError):
    """The model returned output that violates the tool protocol."""


class CompletionRejected(AgentError):
    """The model requested finish before program-owned checks passed."""


class BudgetExceeded(AgentError):
    """A step, call, token, or time budget was exhausted."""


class RunCancelled(AgentError):
    """The control plane cancelled the run."""


class UnsafeExecutionError(AgentError):
    """A live model was paired with a non-sandboxed executor."""
