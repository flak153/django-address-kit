import pytest

from django_address_kit.providers.base import RateLimitError, RetryConfig
from django_address_kit.resolvers import (
    create_address_from_components,
    create_address_from_raw,
)
from tests import factories


@pytest.mark.django_db
def test_create_address_from_components_reuses_location(
    country_instance,
    django_assert_num_queries,
):
    address_data = {
        "street_number": "1600",
        "street_name": "Amphitheatre",
        "street_type": "Parkway",
        "street_direction": "N",
        "formatted": "1600 Amphitheatre Parkway",
        "provider": "manual",
        "raw_payload": {"source": "manual"},
        "metadata": {"confidence": 0.9},
    }
    location_data = {
        "country": country_instance.name,
        "country_code": country_instance.code,
        "state": "California",
        "state_code": "CA",
        "locality": "Mountain View",
        "postal_code": "94043",
    }

    with django_assert_num_queries(30, exact=False):
        address = create_address_from_components(
            address_data=address_data,
            location_data=location_data,
            raw="1600 Amphitheatre Parkway, Mountain View, CA 94043",
        )

    assert address.street_direction == "N"
    assert address.locality.name == "Mountain View"
    assert address.locality.state.code == "CA"
    source = address.sources.get(provider="manual")
    assert source.raw_payload["source"] == "manual"
    assert source.normalized_components["address"]["street_number"] == "1600"
    assert source.normalized_components["address_components"] == []
    assert source.metadata["confidence"] == 0.9
    assert source.version == 1
    assert source.normalized_components["geometry"] == {}


@pytest.mark.django_db
def test_create_address_from_raw_parser_fallback(faker, django_assert_num_queries):
    country = factories.create_country(faker, code="US", name="United States")
    factories.create_state(faker, country=country, name="California", code="CA")
    raw = "742 Evergreen Terrace, Springfield, CA 99999"

    with django_assert_num_queries(20, exact=False):
        address = create_address_from_raw(raw)

    assert address.street_name == "Evergreen Terrace"
    assert address.locality.state.code == "CA"
    parser_source = address.sources.get(provider="parser")
    assert parser_source.raw_payload["street_number"] == "742"
    assert parser_source.metadata == {}
    assert parser_source.normalized_components["geometry"] == {}
    assert parser_source.version == 1


class _FlakyAdapter:
    provider_name = "flaky"

    def __init__(self, payload):
        self._payload = payload
        self._calls = 0

    def geocode(self, query):
        self._calls += 1
        if self._calls == 1:
            raise RateLimitError("quota exceeded")
        return self._payload


@pytest.mark.django_db
def test_create_address_from_raw_retries_on_rate_limit(faker, django_assert_num_queries):
    country = factories.create_country(faker, code="US", name="United States")
    factories.create_state(faker, country=country, name="California", code="CA")
    payload = {
        "street_number": "123",
        "street_name": "Retry",
        "street_type": "Road",
        "formatted": "123 Retry Road",
        "location": {
            "country": "United States",
            "country_code": "US",
            "state": "California",
            "state_code": "CA",
            "locality": "Retryville",
            "postal_code": "94110",
        },
        "raw_payload": {"attempt": 2},
        "metadata": {"retries": 1},
    }
    adapter = _FlakyAdapter(payload)

    with django_assert_num_queries(25, exact=False):
        address = create_address_from_raw(
            "123 Retry Road, Retryville, CA 94110",
            geocode_adapter=adapter,
            retry_config=RetryConfig(max_attempts=2, base_delay=0, max_delay=0),
            sleep_func=lambda _: None,
        )

    assert address.street_name == "Retry"
    assert address.locality.name == "Retryville"
    adapter_source = address.sources.get(provider="flaky")
    assert adapter_source.raw_payload["attempt"] == 2
    assert adapter_source.metadata["retries"] == 1
    assert adapter_source.normalized_components["geometry"] == {}
    assert adapter_source.version == 1
    assert not address.identifiers.filter(provider="flaky").exists()


@pytest.mark.django_db
def test_resolver_stores_provider_identifier(locality_instance):
    from django_address_kit.resolvers import create_address_from_components

    location = {
        "locality": locality_instance.name,
        "state": locality_instance.state.name,
        "state_code": locality_instance.state.code,
        "postal_code": locality_instance.postal_code,
        "country": locality_instance.state.country.name,
        "country_code": locality_instance.state.country.code,
    }

    address = create_address_from_components(
        address_data={
            "street_number": "1600",
            "street_name": "Amphitheatre",
            "provider": "google",
            "raw_payload": {"place_id": "GOOGLE123"},
            "metadata": {"place_id": "GOOGLE123"},
        },
        location_data=location,
        raw="1600 Amphitheatre Pkwy",
    )

    identifier = address.identifiers.get(provider="google")
    assert identifier.identifier == "GOOGLE123"
