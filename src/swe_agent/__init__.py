"""Core package for the SWE Agent Harness."""

from .agent import AgentLoop, AgentResult, BudgetExceeded, StepLimitReached
from .context import ContextBudgetExceeded

__version__ = "0.1.0"

__all__ = [
    "AgentLoop",
    "AgentResult",
    "BudgetExceeded",
    "ContextBudgetExceeded",
    "StepLimitReached",
    "__version__",
]

