import json
import os

import pytest
from address.models import Address as LegacyAddress
from django.core.management import call_command

from django_address_kit.ingest import ingest_legacy_address
from django_address_kit.models import Address, AddressIdentifier, AddressSource


@pytest.mark.django_db
def test_ingest_legacy_address_with_structured_fields(faker):
    payload = {
        "line1": "1600 Amphitheatre Pkwy",
        "city": "Mountain View",
        "state": "California",
        "state_code": "CA",
        "postal_code": "94043",
        "country": "United States",
    }

    address = ingest_legacy_address(payload, geocode_missing=False)

    assert address.street_name.startswith("Amphitheatre")
    source = address.sources.get(provider="legacy")
    assert source.raw_payload["line1"] == "1600 Amphitheatre Pkwy"


class DummyAdapter:
    provider_name = "google"

    def __init__(self, payload):
        self._payload = payload

    def geocode(self, query):
        return self._payload


@pytest.mark.django_db
def test_ingest_legacy_address_triggers_geocode(faker):
    payload = {
        "line1": "1600 Amphitheatre Pkwy",
        "city": "",
        "state": "",
        "postal_code": "",
        "country": "United States",
    }
    geocode_payload = {
        "formatted": "1600 Amphitheatre Pkwy, Mountain View, CA 94043",
        "street_number": "1600",
        "street_name": "Amphitheatre",
        "street_type": "Parkway",
        "location": {
            "locality": "Mountain View",
            "state": "California",
            "state_code": "CA",
            "postal_code": "94043",
            "country": "United States",
            "country_code": "US",
        },
        "provider": "google",
        "raw_payload": {},
    }

    adapter = DummyAdapter(geocode_payload)
    address = ingest_legacy_address(payload, geocode_adapter=adapter)

    assert address.locality.name == "Mountain View"
    source = AddressSource.objects.get(address=address, provider="google")
    assert source.normalized_components["address"]["street_number"] == "1600"


class RecordingAdapter:
    provider_name = "google"

    def __init__(self):
        self.queries = []
        self._payloads = {
            "amphitheatre": {
                "street_number": "1600",
                "street_name": "Amphitheatre",
                "route": "Amphitheatre Parkway",
                "formatted": "1600 Amphitheatre Parkway, Mountain View, CA 94043, USA",
                "location": {
                    "locality": "Mountain View",
                    "state": "California",
                    "state_code": "CA",
                    "postal_code": "94043",
                    "country": "United States",
                    "country_code": "US",
                },
                "provider": "google",
                "raw_payload": {"place_id": "GOOGLE1"},
                "metadata": {"place_id": "GOOGLE1"},
            },
            "apple": {
                "street_number": "1",
                "street_name": "Apple Park",
                "route": "Apple Park Way",
                "formatted": "One Apple Park Way, Cupertino, CA 95014, USA",
                "location": {
                    "locality": "Cupertino",
                    "state": "California",
                    "state_code": "CA",
                    "postal_code": "95014",
                    "country": "United States",
                    "country_code": "US",
                },
                "provider": "google",
                "raw_payload": {"place_id": "GOOGLE2"},
                "metadata": {"place_id": "GOOGLE2"},
            },
        }

    def geocode(self, query):
        self.queries.append(query)
        lowered = query.lower()
        if "amphitheatre" in lowered:
            return self._payloads["amphitheatre"]
        if "apple park" in lowered:
            return self._payloads["apple"]
        raise AssertionError(f"Unexpected query: {query}")


@pytest.mark.django_db
def test_ingest_legacy_address_geocodes_raw_payloads():
    adapter = RecordingAdapter()
    first_raw = "1600 Amphitheatre Pkwy, Mountain View, CA 94043"
    second_raw = "One Apple Park Way, Cupertino, CA 95014"

    first = ingest_legacy_address(
        {"raw": first_raw, "country": "United States"},
        geocode_adapter=adapter,
    )
    second = ingest_legacy_address(
        {"raw": second_raw, "country": "United States"},
        geocode_adapter=adapter,
    )
    duplicate = ingest_legacy_address(
        {"raw": first_raw, "country": "United States"},
        geocode_adapter=adapter,
    )

    assert Address.objects.count() == 2
    assert duplicate.id == first.id

    formatted_values = {
        "1600 Amphitheatre Parkway, Mountain View, CA 94043, USA",
        "One Apple Park Way, Cupertino, CA 95014, USA",
    }
    addresses = list(Address.objects.all())
    assert {address.formatted for address in addresses} == formatted_values
    assert {address.raw for address in addresses} == formatted_values
    assert len(adapter.queries) == 3
    assert "Amphitheatre Parkway" in adapter.queries[0]
    assert "Apple Park Way" in adapter.queries[1]
    assert AddressIdentifier.objects.filter(provider="google").count() == 2


@pytest.mark.django_db
def test_management_command_ingests(tmp_path, monkeypatch):
    payload = [
        {
            "line1": "123 Main St",
            "city": "Boston",
            "state": "MA",
            "postal_code": "02129",
            "country": "United States",
        },
        {
            "line1": "1600 Amphitheatre Pkwy",
            "country": "United States",
        },
    ]
    data_file = tmp_path / "addresses.jsonl"
    with data_file.open("w", encoding="utf-8") as handle:
        for entry in payload:
            handle.write(json.dumps(entry) + "\n")

        class DummyAdapter:
            provider_name = "google"

            def __init__(self, api_key):
                self.api_key = api_key

            def geocode(self, query):
                return {
                    "formatted": "1600 Amphitheatre Pkwy, Mountain View, CA 94043",
                    "street_number": "1600",
                    "street_name": "Amphitheatre",
                    "route": "Amphitheatre Pkwy",
                    "location": {
                        "locality": "Mountain View",
                        "state": "California",
                        "state_code": "CA",
                        "postal_code": "94043",
                        "country": "United States",
                        "country_code": "US",
                    },
                    "provider": "google",
                    "raw_payload": {"place_id": "GOOGLE123"},
                    "metadata": {"place_id": "GOOGLE123"},
                }

    monkeypatch.setattr("django_address_kit.ingest.GoogleMapsAdapter", DummyAdapter)

    call_command(
        "ingest_legacy_addresses",
        "--input",
        str(data_file),
        "--geocode-missing",
        "--google-api-key",
        "dummy",
    )

    from django_address_kit.models import Address

    assert Address.objects.count() == 2
    identifiers = AddressIdentifier.objects.filter(provider="google")
    assert identifiers.exists()


@pytest.mark.django_db
def test_ingest_from_legacy_model(tmp_path, settings):
    legacy = LegacyAddress.objects.create(
        raw="742 Evergreen Terrace, Springfield, IL 62704",
        address1="742 Evergreen Terrace",
        locality="Springfield",
        state="IL",
        postal_code="62704",
        country="United States",
    )

    payload = {
        "line1": legacy.address1,
        "city": legacy.locality,
        "state": legacy.state,
        "postal_code": legacy.postal_code,
        "country": legacy.country,
    }

    address = ingest_legacy_address(payload, geocode_missing=False)

    assert address.street_number == "742"
    assert address.locality.name == "Springfield"


@pytest.mark.django_db
def test_generate_sample_legacy_addresses_command():
    call_command("generate_sample_legacy_addresses", "--count", "5", "--duplicate-ratio", "0")
    assert LegacyAddress.objects.count() == 5
    call_command("generate_sample_legacy_addresses", "--count", "5", "--duplicate-ratio", "1")
    assert LegacyAddress.objects.count() == 10


@pytest.mark.django_db
def test_dump_legacy_addresses_command(tmp_path):
    if LegacyAddress.objects.count() == 0:
        call_command("generate_sample_legacy_addresses", "--count", "3", "--duplicate-ratio", "0")

    output = tmp_path / "legacy.jsonl"
    call_command("dump_legacy_addresses", "--output", str(output), "--format", "jsonl")

    lines = output.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == LegacyAddress.objects.count()


@pytest.mark.django_db
def test_ingest_with_live_google_geocode(tmp_path, settings):
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_MAPS_API_KEY env var not provided")

    payloads = [
        {"raw": "1600 Amphitheatre Parkway, Mountain View, CA 94043", "country": "United States"},
        {"raw": "One Apple Park Way, Cupertino, CA 95014", "country": "United States"},
        {"raw": "1600 Amphitheatre Parkway, Mountain View, CA 94043", "country": "United States"},
    ]

    input_file = tmp_path / "google.jsonl"
    with input_file.open("w", encoding="utf-8") as handle:
        for entry in payloads:
            handle.write(json.dumps(entry) + "\n")

    call_command(
        "ingest_legacy_addresses",
        "--input",
        str(input_file),
        "--geocode-missing",
        "--google-api-key",
        api_key,
    )

    count = Address.objects.count()
    assert count >= 2
    assert AddressIdentifier.objects.filter(provider="google").count() == count
