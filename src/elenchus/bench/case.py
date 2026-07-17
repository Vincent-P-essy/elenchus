"""A benchmark case: a pre-authored claim with known ground truth.

Deliberately not LLM-generated — controlling the input claim precisely (and
its truth) isolates what's being measured to the verifier's own
discriminative power, rather than conflating it with how good some upstream
proposer is at making claims in the first place.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from elenchus.claim import Verdict


@dataclass(frozen=True, slots=True)
class BenchCase:
    id: str
    domain: str
    assertion: str
    context: str
    ideal_verdict: Verdict
    files: dict[str, str] = field(default_factory=dict)  # code domain only
    note: str = ""  # why this case is labelled the way it is
