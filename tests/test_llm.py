from __future__ import annotations

import pytest

from elenchus.llm import Usage, UsageTally


def test_tally_cost_matches_price_table() -> None:
    tally = UsageTally()
    tally.add(
        "claude-opus-4-8",
        Usage(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            cache_read_tokens=1_000_000,
            cache_write_tokens=1_000_000,
        ),
    )
    # 5 (input) + 25 (output) + 0.5 (cache read @0.1x) + 6.25 (cache write @1.25x)
    assert tally.cost_usd() == pytest.approx(36.75)
    assert tally.calls == 1


def test_tally_unknown_model_yields_no_cost() -> None:
    tally = UsageTally()
    tally.add("claude-experimental-9", Usage(input_tokens=10))
    assert tally.cost_usd() is None


def test_tally_aggregates_across_models() -> None:
    tally = UsageTally()
    tally.add("claude-opus-4-8", Usage(input_tokens=100, output_tokens=10))
    tally.add("claude-haiku-4-5", Usage(input_tokens=50, output_tokens=5))
    assert tally.calls == 2
    expected = 100 * 5.0 / 1e6 + 10 * 25.0 / 1e6 + 50 * 1.0 / 1e6 + 5 * 5.0 / 1e6
    assert tally.cost_usd() == pytest.approx(expected)


def test_tally_one_unpriced_model_makes_the_whole_total_unknown() -> None:
    tally = UsageTally()
    tally.add("claude-opus-4-8", Usage(input_tokens=100, output_tokens=10))
    tally.add("claude-experimental-9", Usage(input_tokens=50))
    assert tally.cost_usd() is None
