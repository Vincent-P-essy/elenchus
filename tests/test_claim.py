from __future__ import annotations

from elenchus.claim import Claim, Verdict, Verification


def _claim(**overrides: str) -> Claim:
    defaults = {"id": "c1", "domain": "math", "assertion": "2 + 2 = 4", "context": ""}
    defaults.update(overrides)
    return Claim(**defaults)  # type: ignore[arg-type]


def test_uphold_and_revise_are_accepted() -> None:
    assert Verification(verdict=Verdict.UPHOLD, rebuttal="checked out").accepted
    assert Verification(verdict=Verdict.REVISE, rebuttal="mostly right").accepted


def test_reject_is_not_accepted() -> None:
    assert not Verification(verdict=Verdict.REJECT, rebuttal="wrong").accepted


def test_effective_assertion_defaults_to_original() -> None:
    claim = _claim(assertion="the sky is blue")
    verification = Verification(verdict=Verdict.UPHOLD, rebuttal="confirmed")
    assert verification.effective_assertion(claim) == "the sky is blue"


def test_effective_assertion_uses_revision_when_revised() -> None:
    claim = _claim(assertion="51 is prime")
    verification = Verification(
        verdict=Verdict.REVISE, rebuttal="51 = 3 x 17", revised_assertion="51 is not prime"
    )
    assert verification.effective_assertion(claim) == "51 is not prime"


def test_effective_assertion_falls_back_if_revise_has_no_text() -> None:
    claim = _claim(assertion="original")
    verification = Verification(verdict=Verdict.REVISE, rebuttal="no replacement given")
    assert verification.effective_assertion(claim) == "original"


def test_reject_ignores_a_stray_revised_assertion() -> None:
    claim = _claim(assertion="original")
    verification = Verification(
        verdict=Verdict.REJECT, rebuttal="wrong", revised_assertion="irrelevant"
    )
    assert verification.effective_assertion(claim) == "original"
