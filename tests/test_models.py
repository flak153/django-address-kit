import pytest
from django.core.exceptions import ValidationError
from django_address_kit.models import Address, AddressSource, State


@pytest.mark.django_db
def test_state_code_normalized(country_instance, faker):
    state = State(name=faker.state(), code="ca", country=country_instance)
    state.save()

    assert state.code == "CA"


@pytest.mark.django_db
def test_state_requires_name_and_code(country_instance):
    state = State(name="", code="", country=country_instance)

    with pytest.raises(ValidationError):
        state.save()


@pytest.mark.django_db
def test_state_code_unique_per_country(country_instance, faker):
    State.objects.create(name="Alpha", code="AL", country=country_instance)

    second = State(name="Beta", code="AL", country=country_instance)

    with pytest.raises(ValidationError):
        second.save()


@pytest.mark.django_db
def test_address_syncs_route_and_direction(locality_instance, faker):
    address = Address(
        street_number="500",
        street_name="Mission",
        street_direction="n",
        street_type="Street",
        raw="500 Mission Street, San Francisco, CA 94102",
        locality=locality_instance,
    )
    address.save()

    assert address.route == "Mission"
    assert address.street_name == "Mission"
    assert address.street_direction == "N"


@pytest.mark.django_db
def test_address_po_box_detection(locality_instance):
    address = Address(
        street_number="PO Box 42",
        street_name="",
        raw="PO Box 42, San Francisco, CA 94102",
        locality=locality_instance,
    )
    address.save()

    assert address.is_po_box is True


@pytest.mark.django_db
def test_address_postal_code_property(locality_instance):
    address = Address(
        street_number="742",
        street_name="Evergreen Terrace",
        raw="742 Evergreen Terrace, Springfield, CA 99999",
        locality=locality_instance,
    )
    address.postal_code = "99999"

    assert locality_instance.postal_code == "99999"
    assert address.postal_code == "99999"


@pytest.mark.django_db
def test_address_as_dict_includes_extended_fields(address_instance):
    payload = address_instance.as_dict()

    assert payload["street_name"] == "Market"
    assert payload["unit_type"] == "Suite"
    assert payload["unit_number"] == "100"
    assert payload["is_po_box"] is False


@pytest.mark.django_db
def test_address_source_unique_per_provider(address_instance):
    first = AddressSource.objects.create(
        address=address_instance,
        provider="google",
        raw_payload={"place_id": "abc"},
        normalized_components={},
    )

    second = AddressSource.objects.create(
        address=address_instance,
        provider="google",
        version=2,
        raw_payload={"place_id": "def"},
        normalized_components={},
    )

    assert first.version == 1
    assert second.version == 2


@pytest.mark.django_db
def test_address_source_str(address_instance):
    source = AddressSource.objects.create(
        address=address_instance,
        provider="parser",
        raw_payload={},
        normalized_components={},
    )

    assert "parser" in str(source)


@pytest.mark.django_db
def test_address_source_prunes_to_three(address_instance):
    from django_address_kit.resolvers import create_address_from_components

    location_data = {
        "locality": address_instance.locality.name,
        "postal_code": address_instance.locality.postal_code,
        "state": address_instance.locality.state.name,
        "state_code": address_instance.locality.state.code,
        "country": address_instance.locality.state.country.name,
        "country_code": address_instance.locality.state.country.code,
    }

    for idx in range(5):
        create_address_from_components(
            address_data={
                "street_number": address_instance.street_number,
                "street_name": address_instance.street_name,
                "provider": "google",
                "raw_payload": {"idx": idx},
                "metadata": {"seq": idx},
            },
            location_data=location_data,
            raw=address_instance.raw,
        )

    sources = list(
        AddressSource.objects.filter(address=address_instance, provider="google").order_by(
            "-version"
        )
    )
    assert len(sources) == 3
    assert [source.version for source in sources] == [5, 4, 3]
    assert [source.raw_payload["idx"] for source in sources] == [4, 3, 2]
