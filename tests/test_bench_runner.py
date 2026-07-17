from __future__ import annotations

from typing import Any

import pytest

from conftest import FakeLLM, make_call, tool_turn
from elenchus.bench.case import BenchCase
from elenchus.bench.runner import (
    CaseResult,
    _domain_for,
    compute_metrics,
    render_report,
    run_all,
    run_case,
)
from elenchus.claim import Verdict
from elenchus.domains import CodeDomain, MathDomain, ReadingDomain
from elenchus.errors import ElenchusError
from elenchus.llm import UsageTally
from elenchus.prompts import SUBMIT_VERDICT


def _case(**overrides: Any) -> BenchCase:
    defaults: dict[str, Any] = {
        "id": "t1",
        "domain": "math",
        "assertion": "17 is prime",
        "context": "ctx",
        "ideal_verdict": Verdict.UPHOLD,
    }
    defaults.update(overrides)
    return BenchCase(**defaults)


def _result(ideal: Verdict, actual: Verdict, **overrides: Any) -> CaseResult:
    defaults: dict[str, Any] = {
        "case_id": "t1",
        "domain": "math",
        "ideal_verdict": ideal,
        "actual_verdict": actual,
        "rebuttal": "",
        "cost_usd": 0.01,
        "seconds": 0.1,
    }
    defaults.update(overrides)
    return CaseResult(**defaults)


def _verdict_turn(**overrides: Any) -> Any:
    payload: dict[str, Any] = {"verdict": "uphold", "rebuttal": "ok", "revised_assertion": None}
    payload.update(overrides)
    return tool_turn(make_call(SUBMIT_VERDICT, **payload))


# --- CaseResult properties ---


def test_should_accept_true_for_uphold_and_revise() -> None:
    assert _result(Verdict.UPHOLD, Verdict.UPHOLD).should_accept
    assert _result(Verdict.REVISE, Verdict.REVISE).should_accept


def test_should_accept_false_for_reject() -> None:
    assert not _result(Verdict.REJECT, Verdict.REJECT).should_accept


def test_accepted_mirrors_actual_verdict() -> None:
    assert _result(Verdict.REJECT, Verdict.REVISE).accepted
    assert not _result(Verdict.UPHOLD, Verdict.REJECT).accepted


def test_baseline_correct_only_for_upheld_ideal() -> None:
    assert _result(Verdict.UPHOLD, Verdict.UPHOLD).baseline_correct
    assert not _result(Verdict.REVISE, Verdict.REVISE).baseline_correct
    assert not _result(Verdict.REJECT, Verdict.REJECT).baseline_correct


def test_exact_match_requires_identical_verdicts() -> None:
    assert _result(Verdict.REVISE, Verdict.REVISE).exact_match
    assert not _result(Verdict.REVISE, Verdict.UPHOLD).exact_match


# --- domain dispatch ---


def test_domain_for_dispatches_by_name() -> None:
    assert isinstance(_domain_for(_case(domain="math")), MathDomain)
    assert isinstance(_domain_for(_case(domain="reading")), ReadingDomain)
    assert isinstance(_domain_for(_case(domain="code", files={"a.py": "x"})), CodeDomain)


def test_domain_for_rejects_unknown_domain() -> None:
    with pytest.raises(ValueError, match="unknown domain"):
        _domain_for(_case(domain="astrology"))


def test_code_domain_carries_the_case_files() -> None:
    domain = _domain_for(_case(domain="code", files={"a.py": "print(1)"}))
    assert domain.run_tool("read_file", {"path": "a.py"}) == "print(1)"


# --- run_case / run_all ---


def test_run_case_via_runner_records_cost_and_verdict() -> None:
    tally = UsageTally()
    llm = FakeLLM(script=[_verdict_turn(rebuttal="checked it")], tally=tally)
    result = run_case(llm, tally, _case())
    assert result.actual_verdict is Verdict.UPHOLD
    assert result.rebuttal == "checked it"
    assert result.error == ""
    assert result.cost_usd is not None
    assert result.cost_usd > 0


def test_run_case_catches_elenchus_error() -> None:
    tally = UsageTally()
    llm = FakeLLM(script=[ElenchusError("boom")])
    result = run_case(llm, tally, _case())
    assert result.actual_verdict is Verdict.REJECT
    assert result.error == "boom"
    assert result.cost_usd is None


def test_run_all_filters_to_requested_domain() -> None:
    tally = UsageTally()
    script = [_verdict_turn() for _ in range(10)]  # math has 10 cases
    llm = FakeLLM(script=script, tally=tally)
    results = run_all(llm, tally, domains=["math"])
    assert len(results) == 10
    assert {r.domain for r in results} == {"math"}


def test_run_all_covers_every_domain_by_default() -> None:
    tally = UsageTally()
    script = [_verdict_turn() for _ in range(30)]  # 10 cases x 3 domains
    llm = FakeLLM(script=script, tally=tally)
    results = run_all(llm, tally)
    assert len(results) == 30
    assert {r.domain for r in results} == {"math", "reading", "code"}


# --- compute_metrics ---


def test_compute_metrics_precision_recall_and_f1() -> None:
    results = [
        _result(Verdict.UPHOLD, Verdict.UPHOLD),  # TP
        _result(Verdict.REJECT, Verdict.UPHOLD),  # FP
        _result(Verdict.UPHOLD, Verdict.REJECT),  # FN
        _result(Verdict.REJECT, Verdict.REJECT),  # TN
    ]
    m = compute_metrics(results)
    assert m.n == 4
    assert m.accept_precision == pytest.approx(0.5)
    assert m.accept_recall == pytest.approx(0.5)
    assert m.accept_f1 == pytest.approx(0.5)
    assert m.exact_match_rate == pytest.approx(0.5)
    assert m.baseline_accuracy == pytest.approx(0.5)


def test_compute_metrics_total_cost_sums_when_all_present() -> None:
    results = [
        _result(Verdict.UPHOLD, Verdict.UPHOLD, cost_usd=0.01),
        _result(Verdict.UPHOLD, Verdict.UPHOLD, cost_usd=0.02),
    ]
    m = compute_metrics(results)
    assert m.total_cost_usd == pytest.approx(0.03)


def test_compute_metrics_total_cost_none_if_any_missing() -> None:
    results = [
        _result(Verdict.UPHOLD, Verdict.UPHOLD, cost_usd=0.01),
        _result(Verdict.UPHOLD, Verdict.UPHOLD, cost_usd=None),
    ]
    m = compute_metrics(results)
    assert m.total_cost_usd is None


def test_compute_metrics_handles_no_results() -> None:
    m = compute_metrics([])
    assert m.n == 0
    assert m.baseline_accuracy == 0.0
    assert m.accept_precision == 1.0
    assert m.accept_recall == 1.0
    assert m.exact_match_rate == 0.0


# --- render_report ---


def test_render_report_includes_model_and_domain_row() -> None:
    results = [_result(Verdict.UPHOLD, Verdict.UPHOLD, case_id="math-01", domain="math")]
    report = render_report(results, model="claude-opus-4-8")
    assert "claude-opus-4-8" in report
    assert "| math | 1 |" in report


def test_render_report_omits_misses_section_when_all_exact() -> None:
    results = [_result(Verdict.UPHOLD, Verdict.UPHOLD, case_id="math-01")]
    report = render_report(results, model="m")
    assert "## Misses" not in report


def test_render_report_lists_a_verdict_miss() -> None:
    results = [
        _result(Verdict.UPHOLD, Verdict.REJECT, case_id="math-02", rebuttal="wrongly rejected")
    ]
    report = render_report(results, model="m")
    assert "## Misses" in report
    assert "math-02" in report
    assert "expected `uphold`, got `reject`" in report
    assert "wrongly rejected" in report


def test_render_report_lists_an_error_miss_without_verdict_text() -> None:
    results = [_result(Verdict.UPHOLD, Verdict.REJECT, case_id="math-03", error="timeout")]
    report = render_report(results, model="m")
    assert "error — timeout" in report


def test_render_report_cost_is_na_when_unknown() -> None:
    results = [_result(Verdict.UPHOLD, Verdict.UPHOLD, cost_usd=None)]
    report = render_report(results, model="m")
    assert "total cost: n/a" in report
