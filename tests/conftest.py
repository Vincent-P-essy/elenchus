"""Shared fixtures: a scripted LLM and turn-building helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from elenchus.llm import LLMRequest, LLMTurn, TextBlock, ToolCall, Usage, UsageTally


@dataclass
class FakeLLM:
    """Scripted stand-in for AnthropicLLM: pops one item per complete() call."""

    script: list[LLMTurn | Exception]
    tally: UsageTally | None = None
    requests: list[LLMRequest] = field(default_factory=list)

    def complete(self, request: LLMRequest) -> LLMTurn:
        self.requests.append(request)
        assert self.script, "FakeLLM script exhausted"
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        if self.tally is not None:
            self.tally.add(request.model, item.usage)
        return item


def make_call(name: str, call_id: str = "call_1", **arguments: Any) -> ToolCall:
    return ToolCall(id=call_id, name=name, input=arguments)


def tool_turn(*calls: ToolCall) -> LLMTurn:
    return LLMTurn(
        content=list(calls),
        raw_content=[
            {"type": "tool_use", "id": c.id, "name": c.name, "input": c.input} for c in calls
        ],
        stop_reason="tool_use",
        usage=Usage(input_tokens=100, output_tokens=10),
    )


def text_turn(text: str) -> LLMTurn:
    return LLMTurn(
        content=[TextBlock(text=text)],
        raw_content=[{"type": "text", "text": text}],
        stop_reason="end_turn",
        usage=Usage(input_tokens=100, output_tokens=10),
    )
