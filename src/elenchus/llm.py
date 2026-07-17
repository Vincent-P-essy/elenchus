"""Thin, typed layer over the Anthropic API — same shape as the LLM layer in
momus/sentier/pythia: local request/turn types (never raw SDK objects) so
the verifier is fully testable with a scripted fake, streaming to avoid
timeouts, and per-model USD cost accounting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from elenchus.errors import VerificationError

#: USD per million tokens (input, output).
MODEL_PRICES: dict[str, tuple[float, float]] = {
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


@dataclass(slots=True)
class TextBlock:
    text: str


@dataclass(slots=True)
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass(slots=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass(slots=True)
class LLMTurn:
    content: list[TextBlock | ToolCall]
    raw_content: list[dict[str, Any]]
    stop_reason: str
    usage: Usage

    @property
    def tool_calls(self) -> list[ToolCall]:
        return [block for block in self.content if isinstance(block, ToolCall)]


@dataclass(slots=True)
class LLMRequest:
    model: str
    system: str
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] = field(default_factory=list)
    tool_choice: dict[str, Any] | None = None
    max_tokens: int = 4_000


class LLMClient(Protocol):
    def complete(self, request: LLMRequest) -> LLMTurn: ...


class UsageTally:
    def __init__(self) -> None:
        self.calls = 0
        self.per_model: dict[str, Usage] = {}

    def add(self, model: str, usage: Usage) -> None:
        self.calls += 1
        agg = self.per_model.setdefault(model, Usage())
        agg.input_tokens += usage.input_tokens
        agg.output_tokens += usage.output_tokens
        agg.cache_read_tokens += usage.cache_read_tokens
        agg.cache_write_tokens += usage.cache_write_tokens

    def cost_usd(self) -> float | None:
        total = 0.0
        for model, usage in self.per_model.items():
            prices = MODEL_PRICES.get(model)
            if prices is None:
                return None
            price_in, price_out = prices
            total += usage.input_tokens * price_in / 1e6
            total += usage.cache_write_tokens * price_in * 1.25 / 1e6
            total += usage.cache_read_tokens * price_in * 0.1 / 1e6
            total += usage.output_tokens * price_out / 1e6
        return total


class AnthropicLLM:
    """Production client. Requires ANTHROPIC_API_KEY (or an `ant auth` profile)."""

    def __init__(self, tally: UsageTally, api_key: str | None = None) -> None:
        import anthropic

        self._anthropic = anthropic
        kwargs: dict[str, Any] = {"max_retries": 3}
        if api_key:
            kwargs["api_key"] = api_key
        self._client = anthropic.Anthropic(**kwargs)
        self.tally = tally

    def complete(self, request: LLMRequest) -> LLMTurn:
        kwargs: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "system": request.system,
            "messages": request.messages,
        }
        if request.tools:
            kwargs["tools"] = request.tools
        if request.tool_choice is not None:
            kwargs["tool_choice"] = request.tool_choice
        else:
            kwargs["thinking"] = {"type": "adaptive"}

        try:
            with self._client.messages.stream(**kwargs) as stream:
                message: Any = stream.get_final_message()
        except self._anthropic.APIStatusError as exc:  # pragma: no cover - network path
            raise VerificationError(f"Anthropic API error: {exc}") from exc
        except self._anthropic.APIConnectionError as exc:  # pragma: no cover - network path
            raise VerificationError(f"could not reach the Anthropic API: {exc}") from exc

        stop_reason = str(message.stop_reason or "")
        if stop_reason == "refusal":
            raise VerificationError("the model declined this request (stop_reason=refusal)")

        turn = LLMTurn(
            content=_parse_blocks(message.content),
            raw_content=[_dump_block(block) for block in message.content],
            stop_reason=stop_reason,
            usage=_parse_usage(message.usage),
        )
        self.tally.add(request.model, turn.usage)
        return turn


def _parse_blocks(content: Any) -> list[TextBlock | ToolCall]:
    blocks: list[TextBlock | ToolCall] = []
    for block in content:
        block_type = getattr(block, "type", "")
        if block_type == "text":
            blocks.append(TextBlock(text=str(block.text)))
        elif block_type == "tool_use":
            raw_input = block.input
            tool_input = dict(raw_input) if isinstance(raw_input, dict) else {}
            blocks.append(ToolCall(id=str(block.id), name=str(block.name), input=tool_input))
    return blocks


def _dump_block(block: Any) -> dict[str, Any]:
    if hasattr(block, "model_dump"):
        dumped = block.model_dump(exclude_none=True)
        if isinstance(dumped, dict):
            return dumped
    return dict(block)


def _parse_usage(usage: Any) -> Usage:
    def _get(name: str) -> int:
        value = getattr(usage, name, 0)
        return int(value) if value else 0

    return Usage(
        input_tokens=_get("input_tokens"),
        output_tokens=_get("output_tokens"),
        cache_read_tokens=_get("cache_read_input_tokens"),
        cache_write_tokens=_get("cache_creation_input_tokens"),
    )
