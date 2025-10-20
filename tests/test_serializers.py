import pytest

from django_address_kit.models import AddressSource
from django_address_kit.models import AddressIdentifier
from django_address_kit.serializers import AddressSerializer


@pytest.mark.django_db
def test_address_serializer_create_normalizes_components(country_instance):
    payload = {
        "raw": "1600 Amphitheatre Parkway, Mountain View, CA 94043",
        "street_number": "1600",
        "street_name": "Amphitheatre",
        "street_type": "Parkway",
        "street_direction": "N",
        "unit_type": "Suite",
        "unit_number": "100",
        "locality": {
            "name": "Mountain View",
            "postal_code": "94043",
            "state": {
                "name": "California",
                "code": "CA",
                "country": {"name": country_instance.name, "code": country_instance.code},
            },
        },
    }

    serializer = AddressSerializer(data=payload)
    assert serializer.is_valid(), serializer.errors
    address = serializer.save()

    assert address.street_direction == "N"
    assert address.locality.state.code == "CA"

    AddressSource.objects.create(
        address=address,
        provider="manual",
        raw_payload={"source": "manual"},
        normalized_components={"address": {"street_number": "1600"}},
    )
    AddressIdentifier.objects.create(address=address, provider="google", identifier="GOOGLE123")

    response_data = AddressSerializer(address).data
    assert len(response_data["sources"]) == 1
    assert response_data["sources"][0]["provider"] == "manual"
    assert response_data["identifiers"][0]["identifier"] == "GOOGLE123"


@pytest.mark.django_db
def test_address_serializer_update_sets_locality(address_instance):
    state = address_instance.locality.state
    country = state.country
    payload = {
        "street_direction": "S",
        "unit_type": "Unit",
        "unit_number": "202",
        "locality": {
            "name": "Oakland",
            "postal_code": "94607",
            "state": {
                "name": state.name,
                "code": state.code,
                "country": {"name": country.name, "code": country.code},
            },
        },
    }

    serializer = AddressSerializer(address_instance, data=payload, partial=True)
    assert serializer.is_valid(), serializer.errors
    updated = serializer.save()

    assert updated.street_direction == "S"
    assert updated.unit_number == "202"
    assert updated.locality.name == "Oakland"

    response_data = AddressSerializer(updated).data
    assert "sources" in response_data
