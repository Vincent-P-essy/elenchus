from __future__ import annotations

from typing import Any

import pytest

from conftest import FakeLLM, make_call, text_turn, tool_turn
from elenchus.claim import Claim, Verdict
from elenchus.domains import CodeDomain, MathDomain
from elenchus.errors import ElenchusError, VerificationError
from elenchus.prompts import SUBMIT_VERDICT
from elenchus.verifier import verify


def _verdict_call(**overrides: Any) -> Any:
    payload: dict[str, Any] = {
        "verdict": "uphold",
        "rebuttal": "Checked the evidence; the claim holds.",
        "revised_assertion": None,
    }
    payload.update(overrides)
    return make_call(SUBMIT_VERDICT, call_id="v1", **payload)


def _claim(**overrides: str) -> Claim:
    defaults = {"id": "c1", "domain": "math", "assertion": "17 is prime", "context": "n/a"}
    defaults.update(overrides)
    return Claim(**defaults)  # type: ignore[arg-type]


def test_uphold_with_no_tool_domain() -> None:
    llm = FakeLLM(script=[tool_turn(_verdict_call())])
    verification = verify(llm, MathDomain(), _claim())
    assert verification.verdict is Verdict.UPHOLD
    assert "Checked" in verification.rebuttal
    # The claim's assertion and context are embedded in the first user message.
    first_text = llm.requests[0].messages[0]["content"][0]["text"]
    assert "17 is prime" in first_text


def test_reject_carries_rebuttal() -> None:
    llm = FakeLLM(
        script=[tool_turn(_verdict_call(verdict="reject", rebuttal="51 = 3 x 17, not prime"))]
    )
    verification = verify(llm, MathDomain(), _claim(assertion="51 is prime"))
    assert verification.verdict is Verdict.REJECT
    assert verification.rebuttal == "51 = 3 x 17, not prime"


def test_revise_carries_revised_assertion() -> None:
    llm = FakeLLM(
        script=[
            tool_turn(
                _verdict_call(
                    verdict="revise",
                    rebuttal="core claim right, number wrong",
                    revised_assertion="the corrected claim",
                )
            )
        ]
    )
    verification = verify(llm, MathDomain(), _claim())
    assert verification.verdict is Verdict.REVISE
    assert verification.revised_assertion == "the corrected claim"


def test_code_domain_tool_loop_reads_file_before_verdict() -> None:
    domain = CodeDomain(files={"a.py": "def f(x=[]): return x"})
    llm = FakeLLM(
        script=[
            tool_turn(make_call("read_file", path="a.py")),
            tool_turn(_verdict_call(rebuttal="confirmed the mutable default")),
        ]
    )
    verification = verify(llm, domain, _claim(domain="code", assertion="mutable default bug"))
    assert verification.verdict is Verdict.UPHOLD
    # The file content must have made it back to the model as a tool result.
    second_request_messages = llm.requests[1].messages
    tool_result = second_request_messages[-1]["content"][0]
    assert tool_result["content"] == "def f(x=[]): return x"


def test_invalid_verdict_is_repaired_once() -> None:
    llm = FakeLLM(
        script=[
            tool_turn(make_call(SUBMIT_VERDICT, call_id="bad", verdict="maybe", rebuttal="")),
            tool_turn(_verdict_call()),
        ]
    )
    verification = verify(llm, MathDomain(), _claim())
    assert verification.verdict is Verdict.UPHOLD
    bounce = llm.requests[1].messages[-1]["content"][0]
    assert bounce["is_error"] is True


def test_blank_rebuttal_on_an_otherwise_valid_verdict_is_repaired() -> None:
    llm = FakeLLM(
        script=[
            tool_turn(
                make_call(
                    SUBMIT_VERDICT,
                    call_id="bad",
                    verdict="uphold",
                    rebuttal="  ",
                    revised_assertion=None,
                )
            ),
            tool_turn(_verdict_call()),
        ]
    )
    verification = verify(llm, MathDomain(), _claim())
    assert verification.verdict is Verdict.UPHOLD
    bounce = llm.requests[1].messages[-1]["content"][0]
    assert bounce["is_error"] is True


def test_second_invalid_verdict_defaults_to_reject() -> None:
    llm = FakeLLM(
        script=[
            tool_turn(make_call(SUBMIT_VERDICT, call_id="bad1", verdict="maybe", rebuttal="")),
            tool_turn(make_call(SUBMIT_VERDICT, call_id="bad2", verdict="also-bad", rebuttal="")),
        ]
    )
    verification = verify(llm, MathDomain(), _claim(), max_iterations=4)
    assert verification.verdict is Verdict.REJECT
    assert "did not conclude" in verification.rebuttal


def test_plain_text_turn_is_reprompted_for_a_verdict() -> None:
    llm = FakeLLM(script=[text_turn("let me think..."), tool_turn(_verdict_call())])
    verification = verify(llm, MathDomain(), _claim())
    assert verification.verdict is Verdict.UPHOLD
    reprompt = llm.requests[1].messages[-1]["content"][0]["text"]
    assert "submit_verdict" in reprompt


def test_no_conclusion_defaults_to_reject_and_forces_final_tool_choice() -> None:
    llm = FakeLLM(script=[text_turn("hmm"), text_turn("still thinking")])
    verification = verify(llm, MathDomain(), _claim(), max_iterations=2)
    assert verification.verdict is Verdict.REJECT
    assert "did not conclude" in verification.rebuttal
    assert llm.requests[-1].tool_choice == {"type": "tool", "name": SUBMIT_VERDICT}


def test_llm_connection_error_defaults_to_reject() -> None:
    llm = FakeLLM(script=[VerificationError("could not reach the API")])
    verification = verify(llm, MathDomain(), _claim())
    assert verification.verdict is Verdict.REJECT


def test_unhandled_elenchus_error_propagates() -> None:
    """A plain ElenchusError (unlike VerificationError) is not swallowed by
    the loop's own try/except, so callers such as the bench runner see it."""
    llm = FakeLLM(script=[ElenchusError("domain misconfigured")])
    with pytest.raises(ElenchusError, match="domain misconfigured"):
        verify(llm, MathDomain(), _claim())


def test_verifier_uses_the_requested_model() -> None:
    llm = FakeLLM(script=[tool_turn(_verdict_call())])
    verify(llm, MathDomain(), _claim(), model="claude-sonnet-5")
    assert llm.requests[0].model == "claude-sonnet-5"


def test_verifier_passes_domain_framing_into_system_prompt() -> None:
    llm = FakeLLM(script=[tool_turn(_verdict_call())])
    domain = MathDomain()
    verify(llm, domain, _claim())
    assert domain.framing() in llm.requests[0].system
