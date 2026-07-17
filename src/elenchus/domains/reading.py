"""Reading-comprehension claims: what a source passage says.

Self-contained like the math domain — the passage is already in the
claim's context. The failure mode this domain targets is specific and
common in the wild: a claim that sounds like a faithful summary but subtly
misstates a detail, a number, or a quote.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ReadingDomain:
    name: str = "reading"

    def framing(self) -> str:
        return (
            "Claims here assert what a source passage says. The full passage is "
            "already in the claim's context below. False claims look like: a detail "
            "that isn't actually in the passage, a conclusion the passage doesn't "
            "support, or a subtly altered number, name, or quote. Re-read the actual "
            "passage text before deciding — do not rely on a paraphrase of it."
        )

    def tools(self) -> list[dict[str, Any]]:
        return []

    def run_tool(self, name: str, tool_input: dict[str, Any]) -> str:
        return f"error: the reading domain has no tools (unexpected call to {name!r})"
