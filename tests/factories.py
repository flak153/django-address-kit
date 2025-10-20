"""Lightweight model factories backed by Faker for test data generation."""

from __future__ import annotations

from typing import Any, Optional

from django_address_kit.models import Address, Country, Locality, State


def create_country(faker, **overrides) -> Country:
    """Return a Country instance with realistic defaults."""

    data: dict[str, Any] = {
        "code": overrides.pop("code", faker.country_code())[:2].upper(),
        "name": overrides.pop("name", faker.country()),
    }
    data.update(overrides)
    return Country.objects.create(**data)


def create_state(faker, *, country: Optional[Country] = None, **overrides) -> State:
    """Return a State associated with the provided country."""

    country = country or create_country(faker)
    data: dict[str, Any] = {
        "name": overrides.pop("name", faker.state()),
        "code": overrides.pop("code", faker.state_abbr()).upper(),
        "country": country,
    }
    data.update(overrides)
    return State.objects.create(**data)


def create_locality(
    faker,
    *,
    state: Optional[State] = None,
    **overrides,
) -> Locality:
    """Return a Locality associated with the provided state."""

    state = state or create_state(faker)
    data: dict[str, Any] = {
        "name": overrides.pop("name", faker.city()),
        "postal_code": overrides.pop("postal_code", faker.postcode()),
        "state": state,
    }
    data.update(overrides)
    return Locality.objects.create(**data)


def create_address(
    faker,
    *,
    locality: Optional[Locality] = None,
    **overrides,
) -> Address:
    """Return an Address with normalized component data."""

    locality = locality or create_locality(faker)
    street_number = overrides.pop("street_number", str(faker.building_number()))
    street_name = overrides.pop("street_name", faker.street_name())
    street_type = overrides.pop("street_type", faker.street_suffix())
    street_direction = overrides.pop("street_direction", "")
    unit_type = overrides.pop("unit_type", "Suite")
    unit_number = overrides.pop("unit_number", faker.random_element(["100", "200", "300"]))

    formatted = (
        f"{street_number} {street_name} {street_type}".strip()
        + (f" {street_direction}" if street_direction else "")
    ).strip()
    raw = (
        f"{formatted}, {locality.name}, {locality.state.code} {locality.postal_code}"
        if locality
        else formatted
    )

    data: dict[str, Any] = {
        "street_number": street_number,
        "street_name": street_name,
        "street_type": street_type,
        "street_direction": street_direction,
        "unit_type": unit_type,
        "unit_number": unit_number,
        "locality": locality,
        "raw": overrides.pop("raw", raw),
        "formatted": overrides.pop("formatted", raw),
        "latitude": overrides.pop("latitude", faker.latitude()),
        "longitude": overrides.pop("longitude", faker.longitude()),
    }
    data.update(overrides)
    return Address.objects.create(**data)
