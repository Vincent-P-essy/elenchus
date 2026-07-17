"""Pluggable domains: what kind of claim this is, and how a verifier can
check it."""

from elenchus.domains.base import Domain
from elenchus.domains.code import CodeDomain
from elenchus.domains.math import MathDomain
from elenchus.domains.reading import ReadingDomain

__all__ = ["CodeDomain", "Domain", "MathDomain", "ReadingDomain"]
