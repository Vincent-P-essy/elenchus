"""The core adversarial loop: claim in, Verification out.

Tool calls (if the domain provides any) run until the model calls
submit_verdict, which is force-invoked on the final iteration so a run
always terminates with a structured result. Anything that prevents a clean
verdict — malformed output, an exhausted iteration budget, an LLM error —
resolves to REJECT. Precision is the default, not the exception.
"""

from __future__ import annotations

from typing import Any

from elenchus.claim import Claim, Verdict, Verification
from elenchus.domains.base import Domain
from elenchus.errors import VerificationError
from elenchus.llm import LLMClient, LLMRequest, ToolCall
from elenchus.prompts import SUBMIT_VERDICT, build_system, submit_verdict_tool, user_prompt

DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_MAX_ITERATIONS = 8


def _tool_result(tool_use_id: str, content: str, is_error: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "tool_result", "tool_use_id": tool_use_id, "content": content}
    if is_error:
        result["is_error"] = True
    return result


def verify(
    llm: LLMClient,
    domain: Domain,
    claim: Claim,
    model: str = DEFAULT_MODEL,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> Verification:
    system = build_system(domain.framing())
    domain_tools = domain.tools()
    tools = [*domain_tools, submit_verdict_tool()]
    domain_tool_names = {tool["name"] for tool in domain_tools}

    initial_prompt = user_prompt(claim.assertion, claim.context)
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": [{"type": "text", "text": initial_prompt}]}
    ]
    repaired = False

    for iteration in range(max_iterations):
        force = iteration >= max_iterations - 1
        try:
            turn = llm.complete(
                LLMRequest(
                    model=model,
                    system=system,
                    messages=list(messages),
                    tools=tools,
                    tool_choice={"type": "tool", "name": SUBMIT_VERDICT} if force else None,
                )
            )
        except VerificationError:
            break
        messages.append({"role": "assistant", "content": turn.raw_content})

        verdict_call = next((c for c in turn.tool_calls if c.name == SUBMIT_VERDICT), None)
        if verdict_call is not None:
            verification = _parse_verdict(verdict_call)
            if verification is not None:
                return verification
            if repaired or force:
                break
            repaired = True
            messages.append(
                {
                    "role": "user",
                    "content": [
                        _tool_result(
                            verdict_call.id,
                            "Invalid verdict payload. Call submit_verdict again with a valid "
                            "verdict ('uphold'/'revise'/'reject') and a non-empty rebuttal.",
                            is_error=True,
                        )
                    ],
                }
            )
            continue

        domain_calls = [c for c in turn.tool_calls if c.name in domain_tool_names]
        if domain_calls:
            results = [_tool_result(c.id, domain.run_tool(c.name, c.input)) for c in domain_calls]
            messages.append({"role": "user", "content": results})
            continue

        messages.append(
            {
                "role": "user",
                "content": [{"type": "text", "text": "Deliver your verdict with submit_verdict."}],
            }
        )

    return Verification(
        verdict=Verdict.REJECT,
        rebuttal="verification did not conclude within its budget; withheld by default",
    )


def _parse_verdict(call: ToolCall) -> Verification | None:
    try:
        verdict = Verdict(call.input["verdict"])
        rebuttal = str(call.input["rebuttal"])
        if not rebuttal.strip():
            return None
        revised = call.input.get("revised_assertion")
        return Verification(
            verdict=verdict,
            rebuttal=rebuttal,
            revised_assertion=str(revised) if revised else None,
        )
    except (KeyError, ValueError, TypeError):
        return None
