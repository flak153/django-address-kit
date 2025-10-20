"""Utilities for resolving normalized location hierarchy.

These helpers centralize the logic for reusing existing Country/State/Locality
records before we fall back to inserting new rows. They are intended to be used
at the boundaries where loosely structured address payloads enter the system
(serializers, geocoding hooks, admin actions, etc.).
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Optional

from django.db import transaction

from .models import Address, AddressIdentifier, AddressSource, Country, Locality, State
from .providers.base import GeocodeAdapter, GeocodeError, RateLimitError, RetryConfig


@dataclass(slots=True)
class LocationPayload:
    """Structured location data extracted from an address payload."""

    country_name: str = ""
    country_code: str = ""
    state_name: str = ""
    state_code: str = ""
    locality_name: str = ""
    postal_code: str = ""

    @classmethod
    def from_mapping(cls, payload: Optional[dict]) -> "LocationPayload":
        if not payload:
            return cls()

        return cls(
            country_name=_clean(payload.get("country", "")),
            country_code=_clean(payload.get("country_code", "")),
            state_name=_clean(payload.get("state", "")),
            state_code=_clean(payload.get("state_code", "")),
            locality_name=_clean(payload.get("locality", "")),
            postal_code=_clean(payload.get("postal_code", "")),
        )


def _clean(value: Optional[str]) -> str:
    return (value or "").strip()


def resolve_country(name: str = "", code: str = "") -> Optional[Country]:
    """Return an existing country record matching the incoming payload."""

    cleaned_name = _clean(name)
    cleaned_code = _clean(code)

    if not cleaned_name and not cleaned_code:
        return None

    lookup = {"code": cleaned_code} if cleaned_code else {"name": cleaned_name}

    existing = Country.objects.filter(**lookup).first()
    if not existing and cleaned_code and cleaned_name:
        existing = Country.objects.filter(name__iexact=cleaned_name).first()
        if existing and cleaned_code and not existing.code:
            existing.code = cleaned_code
            existing.save(update_fields=["code"])
    if existing:
        return existing

    defaults = {}
    if cleaned_name:
        defaults.setdefault("name", cleaned_name)
    if cleaned_code:
        defaults.setdefault("code", cleaned_code)

    return Country.objects.create(**defaults)


def resolve_state(name: str = "", code: str = "", *, country: Optional[Country]) -> Optional[State]:
    """Return a matching state record, scoped to the provided country."""

    cleaned_name = _clean(name)
    cleaned_code = _clean(code)

    if not (cleaned_name or cleaned_code):
        return None

    qs = State.objects.all()
    if country:
        qs = qs.filter(country=country)

    if cleaned_code:
        existing = qs.filter(code__iexact=cleaned_code).first()
        if existing:
            return existing

    if cleaned_name:
        existing = qs.filter(name__iexact=cleaned_name).first()
        if existing:
            return existing

    if not country:
        raise ValueError("Cannot create state without associated country context")

    return State.objects.create(
        name=cleaned_name or cleaned_code,
        code=cleaned_code,
        country=country,
    )


def resolve_locality(
    name: str = "",
    postal_code: str = "",
    *,
    state: Optional[State],
) -> Optional[Locality]:
    """Return a locality, ensuring existing rows are reused when present."""

    cleaned_name = _clean(name)
    cleaned_postal = _clean(postal_code)

    if not cleaned_name and not cleaned_postal:
        return None

    qs = Locality.objects.all()
    if state:
        qs = qs.filter(state=state)

    if cleaned_name:
        qs = qs.filter(name__iexact=cleaned_name)

    if cleaned_postal:
        qs = qs.filter(postal_code__iexact=cleaned_postal)

    existing = qs.first()
    if existing:
        return existing

    if not state:
        raise ValueError("Cannot create locality without state context")

    return Locality.objects.create(
        name=cleaned_name,
        postal_code=cleaned_postal,
        state=state,
    )


@transaction.atomic
def resolve_location(payload: LocationPayload) -> Optional[Locality]:
    """Resolve a locality hierarchy from normalized payload data."""

    country = resolve_country(payload.country_name, payload.country_code)
    state = resolve_state(payload.state_name, payload.state_code, country=country)
    return resolve_locality(payload.locality_name, payload.postal_code, state=state)


def resolve_address_from_components(
    *,
    street_number: str = "",
    street_name: str = "",
    route: str = "",
    street_type: str = "",
    street_direction: str = "",
    unit_type: str = "",
    unit_number: str = "",
    raw: str,
    formatted: str = "",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    is_po_box: Optional[bool] = None,
    is_military: Optional[bool] = None,
    location: LocationPayload,
    provider: str = "",
    raw_payload: Optional[dict] = None,
    components_snapshot: Optional[dict] = None,
    metadata: Optional[dict] = None,
) -> Address:
    """Create or reuse an address record backed by normalized location data."""

    locality = resolve_location(location)

    cleaned_street = _clean(street_name)
    cleaned_route = _clean(route)
    if cleaned_street and not cleaned_route:
        cleaned_route = cleaned_street
    elif cleaned_route and not cleaned_street:
        cleaned_street = cleaned_route

    lookup = {
        "raw": raw,
        "street_number": _clean(street_number),
        "street_name": cleaned_street,
        "locality": locality,
    }

    defaults: dict[str, Any] = {
        "route": cleaned_route,
        "formatted": formatted or raw,
        "latitude": latitude,
        "longitude": longitude,
    }

    if is_po_box is not None:
        defaults["is_po_box"] = bool(is_po_box)
    if is_military is not None:
        defaults["is_military"] = bool(is_military)
    extra_defaults = {
        "street_type": _clean(street_type),
        "street_direction": _clean(street_direction).upper(),
        "unit_type": _clean(unit_type),
        "unit_number": _clean(unit_number),
    }
    defaults.update({field: value for field, value in extra_defaults.items() if value})

    # Remove None defaults so get_or_create does not attempt to persist them.
    defaults = {key: value for key, value in defaults.items() if value is not None}

    address, created = Address.objects.get_or_create(
        **lookup,
        defaults=defaults,
    )

    updates: dict[str, Any] = {}

    if not created and raw and address.raw != raw:
        updates["raw"] = raw
    if cleaned_route and address.route != cleaned_route:
        updates["route"] = cleaned_route
    if cleaned_street and address.street_name != cleaned_street:
        updates["street_name"] = cleaned_street
    for field_name, value in extra_defaults.items():
        if value != getattr(address, field_name):
            updates[field_name] = value
    if formatted and address.formatted != formatted:
        updates["formatted"] = formatted
    if latitude is not None and address.latitude != latitude:
        updates["latitude"] = latitude
    if longitude is not None and address.longitude != longitude:
        updates["longitude"] = longitude
    if is_po_box is not None and address.is_po_box != bool(is_po_box):
        updates["is_po_box"] = bool(is_po_box)
    if is_military is not None and address.is_military != bool(is_military):
        updates["is_military"] = bool(is_military)

    if updates:
        for field, value in updates.items():
            setattr(address, field, value)
        address.save()

    if provider:
        snapshot = components_snapshot or {
            "address": {
                "street_number": address.street_number,
                "street_name": address.street_name,
                "street_type": address.street_type,
                "street_direction": address.street_direction,
                "unit_type": address.unit_type,
                "unit_number": address.unit_number,
                "route": address.route,
                "formatted": address.formatted,
            },
            "location": asdict(location),
            "address_components": [],
            "geometry": {},
        }

        _record_address_source(
            address=address,
            provider=provider,
            snapshot=snapshot,
            raw_payload=raw_payload or {},
            metadata=metadata or {},
        )

    return address


def create_address_from_components(
    *,
    address_data: Optional[dict] = None,
    location_data: Optional[dict] = None,
    raw: str,
) -> Address:
    """Public helper for constructing an address from structured payloads.

    `address_data` is expected to resemble Google or Loqate component payloads,
    while `location_data` contains the country/state/locality identifiers.
    """

    components = address_data or {}
    location = LocationPayload.from_mapping(location_data)
    location_snapshot = asdict(location)
    address_snapshot = {
        "street_number": components.get("street_number", ""),
        "street_name": components.get(
            "street_name", components.get("route", components.get("street", ""))
        ),
        "street_type": components.get("street_type", ""),
        "street_direction": components.get("street_direction", ""),
        "unit_type": components.get("unit_type", ""),
        "unit_number": components.get("unit_number", ""),
        "route": components.get("route", components.get("street_name", "")),
        "formatted": components.get("formatted", components.get("formatted_address", "")),
    }

    return resolve_address_from_components(
        street_number=components.get("street_number", ""),
        street_name=components.get(
            "street_name", components.get("route", components.get("street", ""))
        ),
        route=components.get("route", components.get("street_name", "")),
        street_type=components.get("street_type", ""),
        street_direction=components.get("street_direction", ""),
        unit_type=components.get("unit_type", ""),
        unit_number=components.get("unit_number", ""),
        raw=raw,
        formatted=components.get("formatted", components.get("formatted_address", "")),
        latitude=components.get("latitude"),
        longitude=components.get("longitude"),
        is_po_box=components.get("is_po_box"),
        is_military=components.get("is_military"),
        location=location,
        provider=components.get("provider", ""),
        raw_payload=components.get("raw_payload"),
        components_snapshot={
            "address": address_snapshot,
            "location": location_snapshot,
            "address_components": components.get("address_components", []),
            "geometry": components.get("geometry", {}),
        },
        metadata=components.get("metadata"),
    )


def create_address_from_raw(
    raw: str,
    *,
    geocode_adapter: Optional[GeocodeAdapter] = None,
    geocode_func=None,
    parser=None,
    retry_config: Optional[RetryConfig] = None,
    sleep_func: Optional[Callable[[float], None]] = None,
) -> Address:
    """Create or reuse an address from a free-form string input.

    Args:
        raw: Raw address string supplied by the caller.
        geocode_func: Optional callable accepting the raw string and returning
            structured geocode data (e.g., Google Maps response) as a mapping.
        parser: Optional callable used when `geocode_func` is unavailable;
            defaults to the library's regex-based parser.
    """

    from .utils import parse_address_components, standardize_address

    normalized_raw = standardize_address(raw)
    if not normalized_raw:
        raise ValueError("Address string cannot be empty")

    structured: Optional[dict] = None
    location_data = None

    retry = retry_config or RetryConfig()
    sleeper = sleep_func or time.sleep

    if geocode_adapter:
        delay = retry.base_delay
        attempts = 0
        while attempts < retry.max_attempts:
            try:
                structured = geocode_adapter.geocode(normalized_raw) or {}
                if isinstance(structured, list):
                    structured = structured[0] if structured else {}
                location_data = structured.get("location", structured)
                if structured is not None:
                    structured.setdefault(
                        "provider",
                        getattr(
                            geocode_adapter,
                            "provider_name",
                            geocode_adapter.__class__.__name__.lower(),
                        ),
                    )
                break
            except RateLimitError:
                attempts += 1
                if attempts >= retry.max_attempts:
                    raise
                sleeper(max(0.0, min(delay, retry.max_delay)))
                delay = min(delay * 2, retry.max_delay)
            except GeocodeError:
                structured = {}
                break

    if structured is None and geocode_func:
        structured = geocode_func(normalized_raw) or {}
        if isinstance(structured, list):
            structured = structured[0] if structured else {}
        location_data = structured.get("location", structured)
        if structured is not None:
            structured.setdefault("provider", getattr(geocode_func, "__name__", "callable"))

    if not structured:
        structured = None
        location_data = None

    if structured is None:
        parser = parser or parse_address_components

    if structured is None and parser:
        parsed = parser(normalized_raw) or {}
        structured = {
            "street_number": parsed.get("street_number", ""),
            "street_name": parsed.get("street_name", ""),
            "route": parsed.get("street_name", ""),
            "street_type": parsed.get("street_type", ""),
            "street_direction": parsed.get("street_direction", ""),
            "unit_type": parsed.get("unit_type", ""),
            "unit_number": parsed.get("unit_number", ""),
            "formatted": normalized_raw,
            "is_po_box": bool(parsed.get("po_box")),
            "provider": "parser",
            "raw_payload": parsed,
        }
        location_data = {
            "locality": parsed.get("city", ""),
            "state_code": parsed.get("state", ""),
            "postal_code": parsed.get("zipcode", ""),
        }

    if structured:
        formatted_raw = (
            structured.get("formatted")
            or structured.get("formatted_address")
            or normalized_raw
        )
        formatted_raw = standardize_address(formatted_raw) if formatted_raw else normalized_raw
        return create_address_from_components(
            address_data=structured,
            location_data=location_data,
            raw=formatted_raw,
        )

    address, _ = Address.objects.get_or_create(
        raw=normalized_raw,
        defaults={"formatted": normalized_raw},
    )
    return address


def _record_address_source(
    *,
    address: Address,
    provider: str,
    snapshot: dict,
    raw_payload: dict,
    metadata: dict,
) -> None:
    """Persist provider payload and keep only the latest three versions."""

    existing = AddressSource.objects.filter(address=address, provider=provider)
    last_version = existing.order_by("-version").values_list("version", flat=True).first() or 0

    source = AddressSource.objects.create(
        address=address,
        provider=provider,
        version=last_version + 1,
        raw_payload=raw_payload,
        normalized_components=snapshot,
        metadata=metadata,
    )

    ids_to_keep = list(
        AddressSource.objects.filter(address=address, provider=provider)
        .order_by("-version")
        .values_list("id", flat=True)[:3]
    )
    AddressSource.objects.filter(address=address, provider=provider).exclude(
        id__in=ids_to_keep
    ).delete()

    identifier_value = None
    if provider == "google":
        identifier_value = metadata.get("place_id") or raw_payload.get("place_id")
        results = raw_payload.get("results")
        if not identifier_value and isinstance(results, list) and results:
            identifier_value = results[0].get("place_id")
    elif provider == "loqate":
        identifier_value = metadata.get("id") or raw_payload.get("Id")

    if identifier_value:
        AddressIdentifier.objects.update_or_create(
            provider=provider,
            identifier=str(identifier_value),
            defaults={"address": address},
        )

    return source
