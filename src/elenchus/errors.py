"""Exception hierarchy. Everything user-facing derives from ElenchusError."""

from __future__ import annotations


class ElenchusError(Exception):
    """Base class for failures that should surface as a clean CLI error."""


class VerificationError(ElenchusError):
    """The verifier could not reach a usable verdict."""
