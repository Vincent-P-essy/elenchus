"""Runs every case through the verifier and scores it against ground truth.

Two things are measured, deliberately kept distinct:
- "accepted" precision/recall: of claims elenchus decided to trust (uphold
  or revise), how many deserved it, and of claims that deserved trust, how
  many did elenchus actually keep. This is the decision-relevant number —
  it's what "would this have let something false through" actually means.
- exact-verdict match: the stricter bar of also picking the *right* one of
  the three verdicts (distinguishing a clean uphold from a revise).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from elenchus.bench.case import BenchCase
from elenchus.bench.cases import ALL_CASES
from elenchus.claim import Claim, Verdict
from elenchus.domains import CodeDomain, Domain, MathDomain, ReadingDomain
from elenchus.errors import ElenchusError
from elenchus.llm import LLMClient, UsageTally
from elenchus.verifier import DEFAULT_MODEL, verify

_ACCEPTED = (Verdict.UPHOLD, Verdict.REVISE)


@dataclass(slots=True)
class CaseResult:
    case_id: str
    domain: str
    ideal_verdict: Verdict
    actual_verdict: Verdict
    rebuttal: str
    cost_usd: float | None
    seconds: float
    error: str = ""

    @property
    def should_accept(self) -> bool:
        return self.ideal_verdict in _ACCEPTED

    @property
    def accepted(self) -> bool:
        return self.actual_verdict in _ACCEPTED

    @property
    def exact_match(self) -> bool:
        return self.actual_verdict == self.ideal_verdict

    @property
    def baseline_correct(self) -> bool:
        """Would trusting the claim as-is, with no verification, be right?"""
        return self.ideal_verdict == Verdict.UPHOLD


def _domain_for(case: BenchCase) -> Domain:
    if case.domain == "code":
        return CodeDomain(files=dict(case.files))
    if case.domain == "math":
        return MathDomain()
    if case.domain == "reading":
        return ReadingDomain()
    raise ValueError(f"unknown domain {case.domain!r}")


def run_case(
    llm: LLMClient, tally: UsageTally, case: BenchCase, model: str = DEFAULT_MODEL
) -> CaseResult:
    claim = Claim(id=case.id, domain=case.domain, assertion=case.assertion, context=case.context)
    before = tally.cost_usd()
    started = time.monotonic()
    try:
        result = verify(llm, _domain_for(case), claim, model=model)
    except ElenchusError as exc:
        return CaseResult(
            case_id=case.id,
            domain=case.domain,
            ideal_verdict=case.ideal_verdict,
            actual_verdict=Verdict.REJECT,
            rebuttal="",
            cost_usd=None,
            seconds=time.monotonic() - started,
            error=str(exc),
        )
    elapsed = time.monotonic() - started
    after = tally.cost_usd()
    cost = None if before is None or after is None else after - before
    return CaseResult(
        case_id=case.id,
        domain=case.domain,
        ideal_verdict=case.ideal_verdict,
        actual_verdict=result.verdict,
        rebuttal=result.rebuttal,
        cost_usd=cost,
        seconds=elapsed,
    )


def run_all(
    llm: LLMClient,
    tally: UsageTally,
    model: str = DEFAULT_MODEL,
    domains: list[str] | None = None,
) -> list[CaseResult]:
    results: list[CaseResult] = []
    for domain, cases in ALL_CASES.items():
        if domains and domain not in domains:
            continue
        for case in cases:
            results.append(run_case(llm, tally, case, model=model))
    return results


@dataclass(slots=True)
class Metrics:
    n: int
    baseline_accuracy: float
    accept_precision: float
    accept_recall: float
    accept_f1: float
    exact_match_rate: float
    total_cost_usd: float | None


def compute_metrics(results: list[CaseResult]) -> Metrics:
    n = len(results)
    baseline_correct = sum(r.baseline_correct for r in results)
    tp = sum(1 for r in results if r.should_accept and r.accepted)
    fp = sum(1 for r in results if not r.should_accept and r.accepted)
    fn = sum(1 for r in results if r.should_accept and not r.accepted)
    exact = sum(r.exact_match for r in results)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    costs = [r.cost_usd for r in results if r.cost_usd is not None]
    total_cost = sum(costs) if len(costs) == n else None
    return Metrics(
        n=n,
        baseline_accuracy=baseline_correct / n if n else 0.0,
        accept_precision=precision,
        accept_recall=recall,
        accept_f1=f1,
        exact_match_rate=exact / n if n else 0.0,
        total_cost_usd=total_cost,
    )


def _format_cost(cost: float | None) -> str:
    return f"${cost:.2f}" if cost is not None else "n/a"


def render_report(results: list[CaseResult], model: str) -> str:
    from datetime import datetime, timezone

    overall = compute_metrics(results)
    lines = [
        "# elenchus benchmark report",
        "",
        f"- date: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- model: `{model}`",
        f"- cases: {overall.n} across {len({r.domain for r in results})} domains",
        "",
        f"**baseline (trust every claim as-is) accuracy: {overall.baseline_accuracy:.0%}**",
        "",
        f"**with elenchus verification — precision {overall.accept_precision:.2f} · "
        f"recall {overall.accept_recall:.2f} · F1 {overall.accept_f1:.2f} · "
        f"exact-verdict match {overall.exact_match_rate:.0%}**",
        "",
        f"total cost: {_format_cost(overall.total_cost_usd)}",
        "",
        "## Per domain",
        "",
        "| domain | n | baseline acc. | precision | recall | F1 | exact match |",
        "|---|---|---|---|---|---|---|",
    ]
    by_domain: dict[str, list[CaseResult]] = {}
    for r in results:
        by_domain.setdefault(r.domain, []).append(r)
    for domain, domain_results in sorted(by_domain.items()):
        m = compute_metrics(domain_results)
        lines.append(
            f"| {domain} | {m.n} | {m.baseline_accuracy:.0%} | {m.accept_precision:.2f} | "
            f"{m.accept_recall:.2f} | {m.accept_f1:.2f} | {m.exact_match_rate:.0%} |"
        )

    misses = [r for r in results if not r.exact_match or r.error]
    if misses:
        lines += ["", "## Misses", ""]
        for r in misses:
            if r.error:
                lines.append(f"- **{r.case_id}**: error — {r.error}")
            else:
                lines.append(
                    f"- **{r.case_id}**: expected `{r.ideal_verdict.value}`, "
                    f"got `{r.actual_verdict.value}` — {r.rebuttal}"
                )
    lines.append("")
    return "\n".join(lines)
