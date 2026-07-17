"""Math/logic claims. Self-contained: the premises are in `context`."""

from __future__ import annotations

from elenchus.bench.case import BenchCase
from elenchus.claim import Verdict

CASES: list[BenchCase] = [
    BenchCase(
        id="math-01",
        domain="math",
        assertion="The sum of the integers from 1 to 10 is 55.",
        context="Compute the sum 1 + 2 + 3 + ... + 10.",
        ideal_verdict=Verdict.UPHOLD,
        note="Correct: 10*11/2 = 55.",
    ),
    BenchCase(
        id="math-02",
        domain="math",
        assertion="The sum of the integers from 1 to 10 is 56.",
        context="Compute the sum 1 + 2 + 3 + ... + 10.",
        ideal_verdict=Verdict.REJECT,
        note="Off by one; the correct sum is 55.",
    ),
    BenchCase(
        id="math-03",
        domain="math",
        assertion="17 is a prime number.",
        context="Determine whether 17 is prime.",
        ideal_verdict=Verdict.UPHOLD,
        note="Correct: 17 has no divisors other than 1 and itself.",
    ),
    BenchCase(
        id="math-04",
        domain="math",
        assertion="51 is a prime number.",
        context="Determine whether 51 is prime.",
        ideal_verdict=Verdict.REJECT,
        note="51 = 3 x 17, a classic plausible-looking false prime claim.",
    ),
    BenchCase(
        id="math-05",
        domain="math",
        assertion="A train traveling at 60 mph for 2.5 hours covers 150 miles.",
        context="distance = speed x time, with speed = 60 mph and time = 2.5 hours.",
        ideal_verdict=Verdict.UPHOLD,
        note="Correct: 60 * 2.5 = 150.",
    ),
    BenchCase(
        id="math-06",
        domain="math",
        assertion="A train traveling at 60 mph for 2.5 hours covers 145 miles.",
        context="distance = speed x time, with speed = 60 mph and time = 2.5 hours.",
        ideal_verdict=Verdict.REJECT,
        note="Should be 150 miles, not 145.",
    ),
    BenchCase(
        id="math-07",
        domain="math",
        assertion="5 factorial (5!) equals 120.",
        context="5! = 5 x 4 x 3 x 2 x 1.",
        ideal_verdict=Verdict.UPHOLD,
        note="Correct: 5*4*3*2*1 = 120.",
    ),
    BenchCase(
        id="math-08",
        domain="math",
        assertion=(
            "All squares are rectangles, and this shape is a rectangle, "
            "therefore this shape must be a square."
        ),
        context="Premises: every square is a rectangle. The shape in question is a rectangle.",
        ideal_verdict=Verdict.REJECT,
        note="Invalid inference (affirming the consequent) - a rectangle need not be a square.",
    ),
    BenchCase(
        id="math-09",
        domain="math",
        assertion="In a right triangle with legs of length 3 and 4, the hypotenuse has length 5.",
        context="Pythagorean theorem: hypotenuse^2 = leg1^2 + leg2^2, with legs 3 and 4.",
        ideal_verdict=Verdict.UPHOLD,
        note="Correct: sqrt(3^2 + 4^2) = sqrt(25) = 5.",
    ),
    BenchCase(
        id="math-10",
        domain="math",
        assertion="3.14 is the exact value of pi.",
        context="pi is the ratio of a circle's circumference to its diameter.",
        ideal_verdict=Verdict.REVISE,
        note=(
            "3.14 is a legitimate, widely used approximation, but pi is irrational - "
            "'exact value' is the specific error to correct, not the number itself."
        ),
    ),
]
