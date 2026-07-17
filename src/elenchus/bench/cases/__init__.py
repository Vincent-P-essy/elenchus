"""All benchmark cases, grouped by domain."""

from __future__ import annotations

from elenchus.bench.case import BenchCase
from elenchus.bench.cases.code_cases import CASES as CODE_CASES
from elenchus.bench.cases.math_cases import CASES as MATH_CASES
from elenchus.bench.cases.reading_cases import CASES as READING_CASES

ALL_CASES: dict[str, list[BenchCase]] = {
    "math": MATH_CASES,
    "reading": READING_CASES,
    "code": CODE_CASES,
}

__all__ = ["ALL_CASES", "CODE_CASES", "MATH_CASES", "READING_CASES"]
