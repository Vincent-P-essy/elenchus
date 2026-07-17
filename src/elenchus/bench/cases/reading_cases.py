"""Reading-comprehension claims about two short source passages."""

from __future__ import annotations

from elenchus.bench.case import BenchCase
from elenchus.claim import Verdict

_MERIDIAN = """\
Meridian Robotics was founded in 2019 by three former aerospace engineers who
left their jobs at a satellite manufacturer to build warehouse automation
systems. The company's first product, a pallet-sorting robot called Atlas-1,
shipped to its first customer in early 2021 after eighteen months of
development. By 2023, Meridian had deployed over 400 units across 12
countries and employed 85 people, split roughly evenly between engineering
and operations. The company raised a $30 million Series B in late 2022, led
by Northbridge Ventures, to fund expansion into the European market. Meridian
has never turned a profit, reporting a net loss of $4.2 million in fiscal
year 2023."""

_REEF = """\
The Great Barrier Reef, located off the coast of Queensland, Australia, is
the world's largest coral reef system, stretching over 2,300 kilometers and
comprising more than 2,900 individual reefs. It became a UNESCO World
Heritage Site in 1981. The reef supports an extraordinary diversity of
marine life, including over 1,500 species of fish and 400 species of coral.
Rising sea temperatures have caused significant coral bleaching events,
notably in 2016, 2017, and 2020, which scientists estimate affected roughly
half of the reef's shallow-water corals."""


def _passage(text: str) -> str:
    return f"# Source passage\n{text}"


CASES: list[BenchCase] = [
    BenchCase(
        id="reading-01",
        domain="reading",
        assertion=(
            "Meridian Robotics was founded by three people who previously worked in aerospace."
        ),
        context=_passage(_MERIDIAN),
        ideal_verdict=Verdict.UPHOLD,
        note="Matches: 'three former aerospace engineers'.",
    ),
    BenchCase(
        id="reading-02",
        domain="reading",
        assertion="Meridian Robotics was founded by four former aerospace engineers.",
        context=_passage(_MERIDIAN),
        ideal_verdict=Verdict.REJECT,
        note="The passage says three, not four.",
    ),
    BenchCase(
        id="reading-03",
        domain="reading",
        assertion="The company's first product took about a year and a half to develop.",
        context=_passage(_MERIDIAN),
        ideal_verdict=Verdict.UPHOLD,
        note="'eighteen months' = a year and a half.",
    ),
    BenchCase(
        id="reading-04",
        domain="reading",
        assertion="Meridian's first product, Atlas-1, shipped to its first customer in 2022.",
        context=_passage(_MERIDIAN),
        ideal_verdict=Verdict.REJECT,
        note="The passage says early 2021, not 2022.",
    ),
    BenchCase(
        id="reading-05",
        domain="reading",
        assertion="As of 2023, Meridian had operations in a dozen countries.",
        context=_passage(_MERIDIAN),
        ideal_verdict=Verdict.UPHOLD,
        note="'12 countries' = a dozen.",
    ),
    BenchCase(
        id="reading-06",
        domain="reading",
        assertion="Meridian Robotics turned its first profit in fiscal year 2023.",
        context=_passage(_MERIDIAN),
        ideal_verdict=Verdict.REJECT,
        note="The passage states a net loss of $4.2 million in FY2023, not a profit.",
    ),
    BenchCase(
        id="reading-07",
        domain="reading",
        assertion=(
            "Meridian raised $30 million in Series B funding in 2022 led by Northbridge "
            "Ventures, which made the company profitable that year."
        ),
        context=_passage(_MERIDIAN),
        ideal_verdict=Verdict.REVISE,
        note=(
            "The funding facts are correct, but the passage says Meridian has never "
            "turned a profit - the profitability conclusion should be struck, not the "
            "funding details."
        ),
    ),
    BenchCase(
        id="reading-08",
        domain="reading",
        assertion="The Great Barrier Reef stretches for more than 2,000 kilometers.",
        context=_passage(_REEF),
        ideal_verdict=Verdict.UPHOLD,
        note="'over 2,300 kilometers' supports 'more than 2,000'.",
    ),
    BenchCase(
        id="reading-09",
        domain="reading",
        assertion="The Great Barrier Reef was designated a UNESCO World Heritage Site in 1991.",
        context=_passage(_REEF),
        ideal_verdict=Verdict.REJECT,
        note="The passage says 1981, not 1991.",
    ),
    BenchCase(
        id="reading-10",
        domain="reading",
        assertion=(
            "The passage states that coral bleaching has affected nearly all of the "
            "reef's shallow-water corals."
        ),
        context=_passage(_REEF),
        ideal_verdict=Verdict.REJECT,
        note="The passage says 'roughly half', not 'nearly all' - an overstatement.",
    ),
]
