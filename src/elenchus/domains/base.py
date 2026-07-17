"""The Domain protocol: everything the verifier needs to specialize itself
for a kind of claim, without the core loop knowing any domain specifics."""

from __future__ import annotations

from typing import Any, Protocol


class Domain(Protocol):
    """A domain contributes framing (what kind of claim this is, what a
    good refutation attempt looks like) and, optionally, tools the verifier
    can call to gather evidence beyond what's already in the claim's
    context. Domains with self-contained context (the evidence is already
    in the prompt) simply return an empty tool list — verification is then
    a single model call instead of a tool-use loop."""

    name: str

    def framing(self) -> str:
        """1-3 sentences: what this domain's claims look like, and the
        specific things that tend to make them wrong."""
        ...

    def tools(self) -> list[dict[str, Any]]:
        """Anthropic tool schemas available to the verifier. Empty if the
        claim's context is already everything the verifier needs."""
        ...

    def run_tool(self, name: str, tool_input: dict[str, Any]) -> str:
        """Dispatch one tool call. Only invoked for names from tools()."""
        ...
