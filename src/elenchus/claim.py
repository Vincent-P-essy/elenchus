"""A claim: something an LLM (or anything else) asserted, plus whatever
context the verifier needs to have a chance at checking it. The claim
itself never adjudicates its own truth — that's the verifier's job."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True, slots=True)
class Claim:
    id: str
    domain: str
    assertion: str
    context: str
    metadata: dict[str, str] = field(default_factory=dict)


class Verdict(str, Enum):
    UPHOLD = "uphold"
    REVISE = "revise"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class Verification:
    verdict: Verdict
    rebuttal: str
    revised_assertion: str | None = None

    @property
    def accepted(self) -> bool:
        """Whether the claim (possibly revised) is trusted after review."""
        return self.verdict in (Verdict.UPHOLD, Verdict.REVISE)

    def effective_assertion(self, original: Claim) -> str:
        if self.verdict is Verdict.REVISE and self.revised_assertion:
            return self.revised_assertion
        return original.assertion
