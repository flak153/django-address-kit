"""
Base abstractions for pluggable geocoding adapters.

Adapters are kept intentionally lightweight so downstream projects can
customize authentication and HTTP clients while sharing the same retry
and rate-limit handling inside ``create_address_from_raw``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class GeocodeError(RuntimeError):
    """Non-recoverable geocoding failure."""


class ConfigurationError(GeocodeError):
    """Raised when an adapter is misconfigured."""


class RateLimitError(GeocodeError):
    """Raised when a provider signals that rate limits were exceeded."""


@dataclass(slots=True)
class RetryConfig:
    """Retry/backoff configuration used by address helpers."""

    max_attempts: int = 3
    base_delay: float = 0.5
    max_delay: float = 2.0


class GeocodeAdapter(Protocol):
    """Protocol that all geocode adapters must satisfy."""

    def geocode(self, query: str) -> dict[str, Any]:
        """Return a mapping with address components and optional metadata."""
        ...


__all__ = [
    "ConfigurationError",
    "GeocodeAdapter",
    "GeocodeError",
    "RateLimitError",
    "RetryConfig",
]
