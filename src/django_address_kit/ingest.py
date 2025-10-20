"""Helpers for importing legacy django-address data into django-address-kit."""

from __future__ import annotations

from typing import TYPE_CHECKING, Mapping, MutableMapping, Optional

from .providers.google import GoogleMapsAdapter
from .resolvers import create_address_from_components, create_address_from_raw
from .utils import normalize_string

if TYPE_CHECKING:  # pragma: no cover
    from .models import Address

LegacyMapping = Mapping[str, object]


def ingest_legacy_address(
    legacy_payload: LegacyMapping,
    *,
    geocode_missing: bool = True,
    geocode_adapter=None,
    google_api_key: Optional[str] = None,
) -> "Address":
    """Import a legacy django-address style payload into the new models.

    Args:
        legacy_payload: Mapping containing legacy fields (line1/line2/city/state/etc.).
        geocode_missing: Whether to geocode when structured fields are incomplete.
        geocode_adapter: Optional adapter implementing the Google geocode interface.
        google_api_key: API key used to instantiate GoogleMapsAdapter when needed.

    Returns:
        Address: Persisted address instance with normalized data.
    """

    normalized = _normalize_legacy_payload(legacy_payload)
    raw = normalized["raw"]

    address_data = {
        "street_number": normalized.get("street_number", ""),
        "street_name": normalized.get("street_name", ""),
        "route": normalized.get("route", ""),
        "street_type": normalized.get("street_type", ""),
        "street_direction": normalized.get("street_direction", ""),
        "unit_type": normalized.get("unit_type", ""),
        "unit_number": normalized.get("unit_number", ""),
        "formatted": normalized.get("formatted", raw),
        "provider": "legacy",
        "raw_payload": dict(legacy_payload),
        "metadata": {},
    }
    location_data = {
        "locality": normalized.get("locality", ""),
        "postal_code": normalized.get("postal_code", ""),
        "state": normalized.get("state", ""),
        "state_code": normalized.get("state_code", ""),
        "country": normalized.get("country", ""),
        "country_code": normalized.get("country_code", ""),
    }

    has_street = (
        address_data["street_number"] or address_data["route"] or address_data["street_name"]
    )
    has_locality = location_data["locality"] and (
        location_data["state_code"] or location_data["state"]
    )

    if has_street and has_locality:
        return create_address_from_components(
            address_data=address_data,
            location_data=location_data,
            raw=raw,
        )

    if not geocode_missing:
        return create_address_from_raw(raw)

    adapter = geocode_adapter or (
        GoogleMapsAdapter(api_key=google_api_key) if google_api_key else None
    )
    return create_address_from_raw(raw, geocode_adapter=adapter)


def _normalize_legacy_payload(payload: LegacyMapping) -> MutableMapping[str, str]:
    """Best-effort normalization from legacy django-address fields."""

    data: MutableMapping[str, str] = {}

    # Extract common legacy field names.
    line1 = _first_non_empty(payload, ["line1", "street", "street_line_1", "street1", "address1"])
    line2 = _first_non_empty(payload, ["line2", "street_line_2", "street2", "address2"])

    city = _first_non_empty(payload, ["city", "locality"])
    state = _first_non_empty(payload, ["state", "state_name"])
    state_code = _first_non_empty(payload, ["state_code", "province", "state_iso"])
    postal_code = _first_non_empty(payload, ["postal_code", "zip", "zipcode"])
    country = _first_non_empty(payload, ["country", "country_name"])
    country_code = _first_non_empty(payload, ["country_code", "country_iso"])

    unit = _first_non_empty(payload, ["unit", "suite", "apartment", "apt", "unit_number"])

    raw_input = payload.get("raw") if isinstance(payload.get("raw"), str) else ""
    normalized_raw_input = normalize_string(raw_input) if raw_input else ""

    data["street_number"], data["route"] = _split_line(line1)
    data["street_name"] = data["route"]

    formatted = normalize_string(" ".join(filter(None, [line1, line2]))).strip()
    if formatted:
        data["formatted"] = formatted
    elif normalized_raw_input:
        data["formatted"] = normalized_raw_input
    if unit:
        data["unit_number"] = unit

    data["locality"] = city
    data["state"] = state
    data["state_code"] = state_code or state
    data["postal_code"] = postal_code
    data["country"] = country
    data["country_code"] = country_code

    raw_value = normalized_raw_input or _build_raw_string(
        line1, line2, city, state_code or state, postal_code, country
    )
    data["raw"] = raw_value

    return data


def _build_raw_string(line1, line2, city, state, postal_code, country) -> str:
    segments = [line1, line2, ", ".join(filter(None, [city, state])), postal_code, country]
    return normalize_string(", ".join(filter(None, segments)))


def _split_line(line: Optional[str]) -> tuple[str, str]:
    if not line:
        return "", ""
    parts = normalize_string(line).split()
    if parts and parts[0].isdigit():
        return parts[0], " ".join(parts[1:])
    return "", " ".join(parts)


def _first_non_empty(payload: LegacyMapping, keys: list[str]) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_string(value)
    return ""


__all__ = ["ingest_legacy_address"]
