"""DNA Genotek exceptions."""

from __future__ import annotations


class DNAGenotekAuthenticationError(Exception):
    """Raised when DNA Genotek authentication fails."""


class DNAGenotekOrderNotFoundError(Exception):
    """Raised when a DNA Genotek Order is not found."""
