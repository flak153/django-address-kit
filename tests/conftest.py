"""Shared pytest fixtures for django-address-kit."""

from __future__ import annotations

import random

import pytest

from . import factories

pytest_plugins = ["pytest_django"]

try:  # pragma: no cover - exercised in integration tests
    from faker import Faker  # type: ignore
except Exception:  # pragma: no cover - fallback when Faker is unavailable

    class Faker:  # type: ignore
        """Minimal fallback Faker implementation for offline test environments."""

        _COUNTRIES = [("US", "United States"), ("CA", "Canada"), ("GB", "United Kingdom")]
        _STATES = [("CA", "California"), ("NY", "New York"), ("TX", "Texas")]
        _CITIES = ["San Francisco", "New York", "Austin", "Seattle"]
        _STREET_SUFFIXES = ["Street", "Avenue", "Road", "Boulevard", "Parkway"]

        def __init__(self) -> None:
            self._rand = random.Random(8675309)

        def country_code(self) -> str:
            return self._rand.choice(self._COUNTRIES)[0]

        def country(self) -> str:
            return self._rand.choice(self._COUNTRIES)[1]

        def state(self) -> str:
            return self._rand.choice(self._STATES)[1]

        def state_abbr(self) -> str:
            return self._rand.choice(self._STATES)[0]

        def city(self) -> str:
            return self._rand.choice(self._CITIES)

        def postcode(self) -> str:
            return str(self._rand.randint(10000, 99999))

        def building_number(self) -> str:
            return str(self._rand.randint(1, 999))

        def street_name(self) -> str:
            return self._rand.choice(["Market", "Mission", "Elm", "Oak", "Pine"])

        def street_suffix(self) -> str:
            return self._rand.choice(self._STREET_SUFFIXES)

        def random_element(self, elements):
            return self._rand.choice(elements)

        def latitude(self) -> float:
            return round(self._rand.uniform(-90, 90), 6)

        def longitude(self) -> float:
            return round(self._rand.uniform(-180, 180), 6)


@pytest.fixture(scope="session")
def faker() -> Faker:
    """Provide a module-scoped Faker instance."""

    return Faker()


@pytest.fixture
def country_instance(db, faker: Faker):
    """Create a reusable United States country instance."""

    return factories.create_country(faker, code="US", name="United States")


@pytest.fixture
def state_instance(db, faker: Faker, country_instance):
    """Create a reusable California state instance."""

    return factories.create_state(
        faker,
        country=country_instance,
        name="California",
        code="CA",
    )


@pytest.fixture
def locality_instance(db, faker: Faker, state_instance):
    """Create a reusable San Francisco locality instance."""

    return factories.create_locality(
        faker,
        state=state_instance,
        name="San Francisco",
        postal_code="94102",
    )


@pytest.fixture
def address_instance(db, faker: Faker, locality_instance):
    """Create a reusable address instance for tests."""

    return factories.create_address(
        faker,
        locality=locality_instance,
        street_number="123",
        street_name="Market",
        street_type="Street",
        unit_type="Suite",
        unit_number="100",
    )
