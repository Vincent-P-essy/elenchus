"""Command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

import click

from elenchus import __version__
from elenchus.bench.cases import ALL_CASES
from elenchus.bench.runner import compute_metrics, render_report, run_all
from elenchus.claim import Claim
from elenchus.domains import CodeDomain, MathDomain, ReadingDomain
from elenchus.errors import ElenchusError
from elenchus.llm import AnthropicLLM, UsageTally
from elenchus.verifier import DEFAULT_MODEL, verify

_DOMAINS = {"code": CodeDomain, "math": MathDomain, "reading": ReadingDomain}


@click.group(help="elenchus — an independent adversarial pass for LLM claims.")
@click.version_option(__version__, prog_name="elenchus")
def main() -> None: ...


@main.command(help="Verify one claim.")
@click.option("--domain", type=click.Choice(sorted(_DOMAINS)), default="reading", show_default=True)
@click.option("--assertion", required=True, help="The claim to verify.")
@click.option("--context", default="", help="Evidence available to the verifier.")
@click.option("--model", default=DEFAULT_MODEL, show_default=True)
def verify_claim(domain: str, assertion: str, context: str, model: str) -> None:
    tally = UsageTally()
    try:
        llm = AnthropicLLM(tally=tally)
    except Exception as exc:
        raise click.ClickException(
            f"could not initialise the Anthropic client: {exc}\n"
            "Set ANTHROPIC_API_KEY (or authenticate with `ant auth login`)."
        ) from exc
    claim = Claim(id="cli", domain=domain, assertion=assertion, context=context)
    try:
        result = verify(llm, _DOMAINS[domain](), claim, model=model)
    except ElenchusError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"verdict: {result.verdict.value}")
    click.echo(f"rebuttal: {result.rebuttal}")
    if result.revised_assertion:
        click.echo(f"revised: {result.revised_assertion}")
    cost = tally.cost_usd()
    click.echo(f"cost: {'$' + format(cost, '.4f') if cost is not None else 'n/a'}")


@main.command(help="Run the benchmark: does verification improve accuracy?")
@click.option("--model", default=DEFAULT_MODEL, show_default=True)
@click.option(
    "--domain",
    "domains",
    multiple=True,
    type=click.Choice(sorted(ALL_CASES)),
    help="Restrict to one or more domains (default: all).",
)
@click.option(
    "--report",
    "report_path",
    type=click.Path(path_type=Path),
    default=Path("bench-report.md"),
    show_default=True,
)
@click.option(
    "--json",
    "json_path",
    type=click.Path(path_type=Path),
    default=Path("bench-report.json"),
    show_default=True,
)
def bench(model: str, domains: tuple[str, ...], report_path: Path, json_path: Path) -> None:
    tally = UsageTally()
    try:
        llm = AnthropicLLM(tally=tally)
    except Exception as exc:
        raise click.ClickException(
            f"could not initialise the Anthropic client: {exc}\n"
            "Set ANTHROPIC_API_KEY (or authenticate with `ant auth login`)."
        ) from exc

    domain_filter = list(domains) if domains else None
    results = run_all(llm, tally, model=model, domains=domain_filter)
    report = render_report(results, model)
    report_path.write_text(report, encoding="utf-8")
    json_path.write_text(
        json.dumps(
            [
                {
                    "case_id": r.case_id,
                    "domain": r.domain,
                    "ideal_verdict": r.ideal_verdict.value,
                    "actual_verdict": r.actual_verdict.value,
                    "rebuttal": r.rebuttal,
                    "cost_usd": r.cost_usd,
                    "seconds": r.seconds,
                    "error": r.error,
                }
                for r in results
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    click.echo(report)
    metrics = compute_metrics(results)
    if metrics.accept_precision < 0.5:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
