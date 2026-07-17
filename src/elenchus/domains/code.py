"""Code claims: a described bug, behavior, or fix in a small in-memory
repository. The one domain with a real tool, mirroring how momus's
verifier actually investigates (read_file over the repo) rather than
judging from the diff text alone."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CodeDomain:
    files: dict[str, str] = field(default_factory=dict)
    name: str = "code"

    def framing(self) -> str:
        return (
            "Claims here assert something about a piece of source code — a described "
            "bug, a claimed behavior, a claimed fix. False claims in this domain look "
            "like: a bug that doesn't actually exist, a bug that's already guarded "
            "against elsewhere in the file, or a severity/description that doesn't "
            "match what the code actually does. Read the relevant file before deciding "
            "— never judge from the claim's wording alone."
        )

    def tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "read_file",
                "description": "Read a file from the repository under review.",
                "strict": True,
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                    "additionalProperties": False,
                },
            }
        ]

    def run_tool(self, name: str, tool_input: dict[str, Any]) -> str:
        path = str(tool_input.get("path", ""))
        content = self.files.get(path)
        if content is None:
            available = ", ".join(sorted(self.files)) or "(none)"
            return f"error: no such file {path!r}. Available files: {available}"
        return content
