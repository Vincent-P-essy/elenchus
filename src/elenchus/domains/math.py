"""Math/logic claims: a numeric result or a conclusion from stated premises.

Self-contained by design — the premises are already in the claim's context,
so verification here is a single model call, not a tool-use loop. Proves
the library works without an agentic loop, not just with one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class MathDomain:
    name: str = "math"

    def framing(self) -> str:
        return (
            "Claims here assert a numeric or logical result — an arithmetic "
            "computation, a count, or a conclusion drawn from stated premises. Every "
            "premise and number you need is already in the claim's context below — "
            "work the problem out yourself step by step rather than trusting the "
            "claim's stated result."
        )

    def tools(self) -> list[dict[str, Any]]:
        return []

    def run_tool(self, name: str, tool_input: dict[str, Any]) -> str:
        return f"error: the math domain has no tools (unexpected call to {name!r})"
