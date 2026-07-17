from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from elenchus.bench.runner import CaseResult
from elenchus.claim import Verdict, Verification
from elenchus.cli import main
from elenchus.errors import ElenchusError


class _FakeAnthropicLLM:
    def __init__(self, tally: Any, api_key: str | None = None) -> None:
        self.tally = tally

    def complete(self, request: Any) -> Any:
        raise AssertionError("the fake client should never be called directly in CLI tests")


class _BrokenAnthropicLLM:
    def __init__(self, tally: Any, api_key: str | None = None) -> None:
        raise RuntimeError("no key configured")


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def patched_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("elenchus.cli.AnthropicLLM", _FakeAnthropicLLM)


def test_version(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "elenchus" in result.output


def test_verify_claim_requires_a_working_client(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("elenchus.cli.AnthropicLLM", _BrokenAnthropicLLM)
    result = runner.invoke(main, ["verify-claim", "--assertion", "17 is prime"])
    assert result.exit_code == 1
    assert "ANTHROPIC_API_KEY" in result.output


def test_bench_requires_a_working_client(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("elenchus.cli.AnthropicLLM", _BrokenAnthropicLLM)
    result = runner.invoke(
        main,
        ["bench", "--report", str(tmp_path / "r.md"), "--json", str(tmp_path / "r.json")],
    )
    assert result.exit_code == 1
    assert "ANTHROPIC_API_KEY" in result.output


def test_verify_claim_prints_the_verdict_and_rebuttal(
    runner: CliRunner, patched_client: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "elenchus.cli.verify",
        lambda llm, domain, claim, model: Verification(
            verdict=Verdict.UPHOLD, rebuttal="checked the working"
        ),
    )
    result = runner.invoke(main, ["verify-claim", "--assertion", "17 is prime"])
    assert result.exit_code == 0, result.output
    assert "verdict: uphold" in result.output
    assert "rebuttal: checked the working" in result.output


def test_verify_claim_prints_the_revision_when_present(
    runner: CliRunner, patched_client: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "elenchus.cli.verify",
        lambda llm, domain, claim, model: Verification(
            verdict=Verdict.REVISE, rebuttal="scope was wrong", revised_assertion="corrected claim"
        ),
    )
    result = runner.invoke(main, ["verify-claim", "--assertion", "x"])
    assert result.exit_code == 0, result.output
    assert "revised: corrected claim" in result.output


def test_verify_claim_omits_revision_line_when_upheld(
    runner: CliRunner, patched_client: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "elenchus.cli.verify",
        lambda llm, domain, claim, model: Verification(verdict=Verdict.UPHOLD, rebuttal="fine"),
    )
    result = runner.invoke(main, ["verify-claim", "--assertion", "x"])
    assert "revised:" not in result.output


def test_verify_claim_surfaces_elenchus_errors_cleanly(
    runner: CliRunner, patched_client: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(llm: Any, domain: Any, claim: Any, model: str) -> Verification:
        raise ElenchusError("iteration budget misconfigured")

    monkeypatch.setattr("elenchus.cli.verify", _boom)
    result = runner.invoke(main, ["verify-claim", "--assertion", "x"])
    assert result.exit_code == 1
    assert "iteration budget misconfigured" in result.output


def test_bench_writes_report_and_json_and_exits_zero_above_threshold(
    runner: CliRunner, patched_client: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    results = [
        CaseResult(
            case_id="math-01",
            domain="math",
            ideal_verdict=Verdict.UPHOLD,
            actual_verdict=Verdict.UPHOLD,
            rebuttal="ok",
            cost_usd=0.01,
            seconds=0.1,
        )
    ]
    monkeypatch.setattr("elenchus.cli.run_all", lambda llm, tally, model, domains: results)
    report_path = tmp_path / "report.md"
    json_path = tmp_path / "report.json"
    result = runner.invoke(main, ["bench", "--report", str(report_path), "--json", str(json_path)])
    assert result.exit_code == 0, result.output
    assert report_path.exists()
    payload = json.loads(json_path.read_text())
    assert payload[0]["case_id"] == "math-01"
    assert payload[0]["actual_verdict"] == "uphold"


def test_bench_exits_nonzero_when_precision_is_low(
    runner: CliRunner, patched_client: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    results = [
        CaseResult(
            case_id="math-01",
            domain="math",
            ideal_verdict=Verdict.REJECT,
            actual_verdict=Verdict.UPHOLD,
            rebuttal="wrongly upheld",
            cost_usd=0.01,
            seconds=0.1,
        )
    ]
    monkeypatch.setattr("elenchus.cli.run_all", lambda llm, tally, model, domains: results)
    result = runner.invoke(
        main,
        ["bench", "--report", str(tmp_path / "r.md"), "--json", str(tmp_path / "r.json")],
    )
    assert result.exit_code == 1


def test_bench_forwards_the_domain_filter(
    runner: CliRunner, patched_client: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, Any] = {}

    def fake_run_all(llm: Any, tally: Any, model: str, domains: list[str] | None) -> list[Any]:
        captured["domains"] = domains
        return []

    monkeypatch.setattr("elenchus.cli.run_all", fake_run_all)
    runner.invoke(
        main,
        [
            "bench",
            "--domain",
            "math",
            "--domain",
            "code",
            "--report",
            str(tmp_path / "r.md"),
            "--json",
            str(tmp_path / "r.json"),
        ],
    )
    assert captured["domains"] == ["math", "code"]
