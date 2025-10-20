"""Utilities for interfacing with the legacy django-address package during tests."""

from __future__ import annotations

try:  # pragma: no cover - we exercise this when the optional extra is installed
    from address.models import Address as LegacyAddress
except Exception:  # pragma: no cover
    LegacyAddress = None  # type: ignore


def legacy_payload_from_instance(instance) -> dict:
    """Convert a legacy django-address Address instance to the ingestion payload format."""

    if LegacyAddress is None:
        raise RuntimeError("django-address is not installed; install the 'legacy' extra")

    return {
        "line1": instance.raw or "",
        "city": getattr(instance, "locality", ""),
        "state": getattr(instance, "state", ""),
        "postal_code": getattr(instance, "postal_code", ""),
        "country": getattr(instance, "country", ""),
    }


__all__ = ["LegacyAddress", "legacy_payload_from_instance"]
