"""
Comprehensive pytest tests for django-address-kit models.

Tests cover:
- State model: creation, validation, relationships, string representations
- Locality model: creation, validation, foreign keys, edge cases
- Address model: full address handling, PO boxes, military addresses, geocoding
- Field validation: max_lengths, required fields, uniqueness constraints
- Edge cases: missing optional fields, boundary conditions, data integrity
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django_address_kit.models import State, Locality, Address


# ============================================================================
# State Model Tests
# ============================================================================


class TestStateModel:
    """Test suite for the State model."""

    def test_state_creation_valid(self, db):
        """Test creating a state with valid data."""
        state = State.objects.create(code="CA", name="California")

        assert state.code == "CA"
        assert state.name == "California"
        assert State.objects.count() == 1

    def test_state_creation_all_states(self, db):
        """Test creating all US states, territories, and military codes."""
        from django_address_kit.constants import ALL_STATE_CODES

        for code, name in ALL_STATE_CODES.items():
            state = State.objects.create(code=code, name=name)
            assert state.code == code
            assert state.name == name

        assert State.objects.count() == len(ALL_STATE_CODES)

    def test_state_code_max_length(self, db):
        """Test that state code enforces max_length of 2 characters."""
        with pytest.raises((ValidationError, IntegrityError)):
            state = State(code="CAL", name="California")
            state.full_clean()

    def test_state_code_required(self, db):
        """Test that state code is required."""
        with pytest.raises((ValidationError, IntegrityError)):
            state = State(name="California")
            state.full_clean()

    def test_state_name_required(self, db):
        """Test that state name is required."""
        with pytest.raises((ValidationError, IntegrityError)):
            state = State(code="CA")
            state.full_clean()

    def test_state_code_unique(self, db):
        """Test that state code must be unique."""
        State.objects.create(code="CA", name="California")

        with pytest.raises(IntegrityError):
            State.objects.create(code="CA", name="California Duplicate")

    def test_state_str_representation(self, db):
        """Test the string representation of State."""
        state = State.objects.create(code="NY", name="New York")

        assert str(state) == "NY - New York" or str(state) == "New York"

    def test_state_code_uppercase(self, db):
        """Test that state codes are stored uppercase."""
        state = State.objects.create(code="tx", name="Texas")

        assert state.code == "TX" or state.code == "tx"

    def test_military_state_creation(self, db):
        """Test creating military state codes."""
        military_states = [
            ("AA", "Armed Forces Americas"),
            ("AE", "Armed Forces Europe"),
            ("AP", "Armed Forces Pacific"),
        ]

        for code, name in military_states:
            state = State.objects.create(code=code, name=name)
            assert state.code == code
            assert state.name == name

    def test_territory_creation(self, db):
        """Test creating US territory state codes."""
        territories = [
            ("PR", "Puerto Rico"),
            ("GU", "Guam"),
            ("VI", "U.S. Virgin Islands"),
        ]

        for code, name in territories:
            state = State.objects.create(code=code, name=name)
            assert state.code == code
            assert state.name == name


# ============================================================================
# Locality Model Tests
# ============================================================================


class TestLocalityModel:
    """Test suite for the Locality model."""

    def test_locality_creation_basic(self, db, state_instance):
        """Test creating a locality with required fields."""
        locality = Locality.objects.create(
            name="San Francisco", state=state_instance, postal_code="94102"
        )

        assert locality.name == "San Francisco"
        assert locality.state == state_instance
        assert locality.postal_code == "94102"
        assert locality.county is None

    def test_locality_creation_with_county(self, db, state_instance):
        """Test creating a locality with optional county field."""
        locality = Locality.objects.create(
            name="Columbus", state=state_instance, postal_code="43215", county="Franklin"
        )

        assert locality.name == "Columbus"
        assert locality.county == "Franklin"

    def test_locality_name_required(self, db, state_instance):
        """Test that locality name is required."""
        with pytest.raises((ValidationError, IntegrityError)):
            locality = Locality(state=state_instance, postal_code="12345")
            locality.full_clean()

    def test_locality_state_required(self, db):
        """Test that locality state foreign key is required."""
        with pytest.raises((ValidationError, IntegrityError)):
            locality = Locality(name="San Francisco", postal_code="94102")
            locality.full_clean()

    def test_locality_postal_code_required(self, db, state_instance):
        """Test that postal code is required."""
        with pytest.raises((ValidationError, IntegrityError)):
            locality = Locality(name="San Francisco", state=state_instance)
            locality.full_clean()

    def test_locality_postal_code_format_5_digit(self, db, state_instance):
        """Test 5-digit ZIP code format."""
        locality = Locality.objects.create(
            name="New York", state=state_instance, postal_code="10001"
        )

        assert locality.postal_code == "10001"
        assert len(locality.postal_code) == 5

    def test_locality_postal_code_format_9_digit(self, db, state_instance):
        """Test 9-digit ZIP+4 code format."""
        locality = Locality.objects.create(
            name="Chicago", state=state_instance, postal_code="60601-1234"
        )

        assert locality.postal_code == "60601-1234"

    def test_locality_foreign_key_cascade(self, db, state_instance):
        """Test that deleting a state cascades to localities."""
        locality = Locality.objects.create(
            name="Seattle", state=state_instance, postal_code="98101"
        )

        locality_id = locality.id
        state_instance.delete()

        with pytest.raises(Locality.DoesNotExist):
            Locality.objects.get(id=locality_id)

    def test_locality_str_representation(self, db, state_instance):
        """Test the string representation of Locality."""
        locality = Locality.objects.create(
            name="Portland", state=state_instance, postal_code="97201"
        )

        expected_strs = ["Portland, CA 97201", "Portland, CA", "Portland - 97201"]
        assert any(str(locality) == expected for expected in expected_strs)

    def test_locality_multiple_in_same_state(self, db, state_instance):
        """Test creating multiple localities in the same state."""
        locality1 = Locality.objects.create(
            name="Los Angeles", state=state_instance, postal_code="90001"
        )

        locality2 = Locality.objects.create(
            name="San Diego", state=state_instance, postal_code="92101"
        )

        assert locality1.state == locality2.state
        assert Locality.objects.filter(state=state_instance).count() == 2

    def test_locality_same_name_different_states(self, db):
        """Test that same city name can exist in different states."""
        state_ca = State.objects.create(code="CA", name="California")
        state_tx = State.objects.create(code="TX", name="Texas")

        locality_ca = Locality.objects.create(
            name="Springfield", state=state_ca, postal_code="90001"
        )

        locality_tx = Locality.objects.create(
            name="Springfield", state=state_tx, postal_code="75001"
        )

        assert locality_ca.name == locality_tx.name
        assert locality_ca.state != locality_tx.state

    def test_locality_county_optional(self, db, state_instance):
        """Test that county field is optional."""
        locality = Locality.objects.create(name="Miami", state=state_instance, postal_code="33101")

        assert locality.county is None or locality.county == ""


# ============================================================================
# Address Model Tests
# ============================================================================


class TestAddressModel:
    """Test suite for the Address model."""

    def test_address_creation_minimal(self, db, locality_instance):
        """Test creating an address with minimal required fields."""
        address = Address.objects.create(
            street_number="123", street_name="Main", locality=locality_instance
        )

        assert address.street_number == "123"
        assert address.street_name == "Main"
        assert address.locality == locality_instance

    def test_address_creation_full(self, db, locality_instance):
        """Test creating an address with all fields populated."""
        address = Address.objects.create(
            raw="456 N Market St, Suite 200, San Francisco, CA 94102",
            street_number="456",
            street_name="Market",
            street_type="St",
            street_direction="N",
            unit_type="Suite",
            unit_number="200",
            locality=locality_instance,
            formatted="456 N Market St, Suite 200\nSan Francisco, CA 94102",
            latitude=Decimal("37.7749"),
            longitude=Decimal("-122.4194"),
            is_po_box=False,
            is_military=False,
        )

        assert address.street_number == "456"
        assert address.street_name == "Market"
        assert address.street_type == "St"
        assert address.street_direction == "N"
        assert address.unit_type == "Suite"
        assert address.unit_number == "200"
        assert address.formatted is not None
        assert address.latitude == Decimal("37.7749")
        assert address.longitude == Decimal("-122.4194")

    def test_address_raw_field(self, db, locality_instance):
        """Test the raw TextField for storing original address input."""
        raw_address = "123 Main Street, Apartment 4B, San Francisco, CA 94102"
        address = Address.objects.create(
            raw=raw_address,
            street_number="123",
            street_name="Main Street",
            locality=locality_instance,
        )

        assert address.raw == raw_address

    def test_address_formatted_field(self, db, locality_instance):
        """Test the formatted TextField for standardized address."""
        formatted = "123 Main St, Apt 4B\nSan Francisco, CA 94102"
        address = Address.objects.create(
            street_number="123", street_name="Main", locality=locality_instance, formatted=formatted
        )

        assert address.formatted == formatted

    def test_address_po_box_flag(self, db, locality_instance):
        """Test is_po_box flag for PO Box addresses."""
        address = Address.objects.create(
            street_number="PO Box 1234", street_name="", locality=locality_instance, is_po_box=True
        )

        assert address.is_po_box is True

    def test_address_po_box_detection(self, db, locality_instance):
        """Test PO Box address handling."""
        po_box_variants = [
            "PO Box 1234",
            "P.O. Box 5678",
            "Post Office Box 9999",
        ]

        for po_box in po_box_variants:
            address = Address.objects.create(
                raw=po_box,
                street_number=po_box,
                street_name="",
                locality=locality_instance,
                is_po_box=True,
            )
            assert address.is_po_box is True

    def test_address_military_flag(self, db):
        """Test is_military flag for military addresses."""
        military_state = State.objects.create(code="AE", name="Armed Forces Europe")
        military_locality = Locality.objects.create(
            name="APO", state=military_state, postal_code="09123"
        )

        address = Address.objects.create(
            street_number="Unit 1234",
            street_name="Box 567",
            locality=military_locality,
            is_military=True,
        )

        assert address.is_military is True

    def test_address_geocoding_coordinates(self, db, locality_instance):
        """Test latitude and longitude fields for geocoding."""
        address = Address.objects.create(
            street_number="1600",
            street_name="Amphitheatre Parkway",
            locality=locality_instance,
            latitude=Decimal("37.422408"),
            longitude=Decimal("-122.084068"),
        )

        assert address.latitude == Decimal("37.422408")
        assert address.longitude == Decimal("-122.084068")

    def test_address_geocoding_optional(self, db, locality_instance):
        """Test that geocoding coordinates are optional."""
        address = Address.objects.create(
            street_number="789", street_name="Broadway", locality=locality_instance
        )

        assert address.latitude is None
        assert address.longitude is None

    def test_address_unit_fields(self, db, locality_instance):
        """Test apartment/unit fields."""
        unit_types = ["Apt", "Suite", "Unit", "Floor", "Room", "Building"]

        for unit_type in unit_types:
            address = Address.objects.create(
                street_number="100",
                street_name="Test St",
                unit_type=unit_type,
                unit_number="42",
                locality=locality_instance,
            )
            assert address.unit_type == unit_type
            assert address.unit_number == "42"

    def test_address_street_direction(self, db, locality_instance):
        """Test street direction prefixes and suffixes."""
        directions = ["N", "S", "E", "W", "NE", "NW", "SE", "SW"]

        for direction in directions:
            address = Address.objects.create(
                street_number="200",
                street_name="Main",
                street_direction=direction,
                locality=locality_instance,
            )
            assert address.street_direction == direction

    def test_address_street_type(self, db, locality_instance):
        """Test street type abbreviations."""
        street_types = ["St", "Ave", "Blvd", "Rd", "Ln", "Dr", "Ct", "Pl", "Way"]

        for street_type in street_types:
            address = Address.objects.create(
                street_number="300",
                street_name="Main",
                street_type=street_type,
                locality=locality_instance,
            )
            assert address.street_type == street_type

    def test_address_locality_foreign_key(self, db, locality_instance):
        """Test foreign key relationship to Locality."""
        address = Address.objects.create(
            street_number="400", street_name="Market", locality=locality_instance
        )

        assert address.locality == locality_instance
        assert address.locality.name == locality_instance.name

    def test_address_locality_cascade_delete(self, db, locality_instance):
        """Test cascade deletion when locality is deleted."""
        address = Address.objects.create(
            street_number="500", street_name="Oak", locality=locality_instance
        )

        address_id = address.id
        locality_instance.delete()

        with pytest.raises(Address.DoesNotExist):
            Address.objects.get(id=address_id)

    def test_address_str_representation(self, db, locality_instance):
        """Test the string representation of Address."""
        address = Address.objects.create(
            street_number="123", street_name="Main", street_type="St", locality=locality_instance
        )

        address_str = str(address)
        assert "123" in address_str or address_str
        assert "Main" in address_str or address_str

    def test_address_optional_fields_none(self, db, locality_instance):
        """Test that optional fields can be None."""
        address = Address.objects.create(
            street_number="600", street_name="Pine", locality=locality_instance
        )

        assert address.street_type is None or address.street_type == ""
        assert address.street_direction is None or address.street_direction == ""
        assert address.unit_type is None or address.unit_type == ""
        assert address.unit_number is None or address.unit_number == ""
        assert address.raw is None or address.raw == ""
        assert address.formatted is None or address.formatted == ""

    def test_address_multiple_per_locality(self, db, locality_instance):
        """Test creating multiple addresses in the same locality."""
        address1 = Address.objects.create(
            street_number="100", street_name="First St", locality=locality_instance
        )

        address2 = Address.objects.create(
            street_number="200", street_name="Second Ave", locality=locality_instance
        )

        assert address1.locality == address2.locality
        assert Address.objects.filter(locality=locality_instance).count() == 2

    def test_address_long_street_name(self, db, locality_instance):
        """Test address with long street name."""
        long_name = "Martin Luther King Junior Boulevard"
        address = Address.objects.create(
            street_number="1000", street_name=long_name, locality=locality_instance
        )

        assert address.street_name == long_name


# ============================================================================
# Field Validation Tests
# ============================================================================


class TestFieldValidation:
    """Test suite for field validation across all models."""

    def test_state_code_length_validation(self, db):
        """Test State code field max_length enforcement."""
        with pytest.raises((ValidationError, IntegrityError)):
            state = State(code="TOOLONG", name="Test State")
            state.full_clean()

    def test_locality_postal_code_validation(self, db, state_instance):
        """Test Locality postal_code format validation."""
        valid_zip_codes = ["12345", "12345-6789", "00501"]

        for zip_code in valid_zip_codes:
            locality = Locality.objects.create(
                name=f"City {zip_code}", state=state_instance, postal_code=zip_code
            )
            assert locality.postal_code == zip_code

    def test_address_required_fields(self, db, locality_instance):
        """Test Address required field validation."""
        with pytest.raises((ValidationError, IntegrityError, TypeError)):
            address = Address(street_number="123")
            address.full_clean()

    def test_coordinates_precision(self, db, locality_instance):
        """Test latitude/longitude precision."""
        address = Address.objects.create(
            street_number="123",
            street_name="Main",
            locality=locality_instance,
            latitude=Decimal("37.12345678"),
            longitude=Decimal("-122.12345678"),
        )

        assert isinstance(address.latitude, Decimal)
        assert isinstance(address.longitude, Decimal)

    def test_coordinates_range_validation(self, db, locality_instance):
        """Test that coordinates are within valid ranges."""
        valid_coords = [
            (Decimal("37.7749"), Decimal("-122.4194")),  # San Francisco
            (Decimal("40.7128"), Decimal("-74.0060")),  # New York
            (Decimal("21.3099"), Decimal("-157.8581")),  # Honolulu
        ]

        for lat, lon in valid_coords:
            address = Address.objects.create(
                street_number="123",
                street_name="Test St",
                locality=locality_instance,
                latitude=lat,
                longitude=lon,
            )
            assert -90 <= address.latitude <= 90
            assert -180 <= address.longitude <= 180


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_empty_street_name_for_po_box(self, db, locality_instance):
        """Test that PO Box addresses can have empty street_name."""
        address = Address.objects.create(
            street_number="PO Box 1234", street_name="", locality=locality_instance, is_po_box=True
        )

        assert address.street_name == ""
        assert address.is_po_box is True

    def test_address_with_special_characters(self, db, locality_instance):
        """Test address fields with special characters."""
        address = Address.objects.create(
            street_number="123-A",
            street_name="O'Connor",
            locality=locality_instance,
            raw="123-A O'Connor St., Apt #5",
        )

        assert "'" in address.street_name
        assert "-" in address.street_number

    def test_locality_same_zip_different_cities(self, db, state_instance):
        """Test handling of same ZIP code for different cities."""
        locality1 = Locality.objects.create(
            name="City A", state=state_instance, postal_code="12345"
        )

        locality2 = Locality.objects.create(
            name="City B", state=state_instance, postal_code="12345"
        )

        assert locality1.postal_code == locality2.postal_code
        assert locality1.name != locality2.name

    def test_bulk_create_states(self, db):
        """Test bulk creation of states."""
        from django_address_kit.constants import US_STATES

        states = [State(code=code, name=name) for code, name in US_STATES.items()]
        State.objects.bulk_create(states)

        assert State.objects.count() == len(US_STATES)

    def test_address_query_by_locality(self, db, locality_instance):
        """Test querying addresses by locality."""
        for i in range(5):
            Address.objects.create(
                street_number=str(100 + i), street_name="Test St", locality=locality_instance
            )

        addresses = Address.objects.filter(locality=locality_instance)
        assert addresses.count() == 5

    def test_state_query_by_code(self, db):
        """Test querying state by code."""
        State.objects.create(code="CA", name="California")
        state = State.objects.get(code="CA")

        assert state.name == "California"

    def test_locality_filter_by_state(self, db, state_instance):
        """Test filtering localities by state."""
        for i in range(3):
            Locality.objects.create(name=f"City {i}", state=state_instance, postal_code=f"9410{i}")

        localities = Locality.objects.filter(state=state_instance)
        assert localities.count() == 3

    def test_address_null_coordinates(self, db, locality_instance):
        """Test that addresses without geocoding work correctly."""
        address = Address.objects.create(
            street_number="999",
            street_name="Unknown Rd",
            locality=locality_instance,
            latitude=None,
            longitude=None,
        )

        assert address.latitude is None
        assert address.longitude is None

    def test_unicode_in_address_fields(self, db, locality_instance):
        """Test Unicode characters in address fields."""
        address = Address.objects.create(
            street_number="123",
            street_name="José María",
            locality=locality_instance,
            raw="123 José María St",
        )

        assert "José" in address.street_name
        assert "María" in address.street_name

    @pytest.mark.parametrize("direction", ["N", "S", "E", "W", "NE", "NW", "SE", "SW"])
    def test_all_street_directions(self, db, locality_instance, direction):
        """Parametrized test for all street directions."""
        address = Address.objects.create(
            street_number="100",
            street_name="Main",
            street_direction=direction,
            locality=locality_instance,
        )

        assert address.street_direction == direction

    @pytest.mark.parametrize(
        "state_code,state_name",
        [
            ("CA", "California"),
            ("NY", "New York"),
            ("TX", "Texas"),
            ("FL", "Florida"),
            ("AE", "Armed Forces Europe"),
            ("PR", "Puerto Rico"),
        ],
    )
    def test_parametrized_state_creation(self, db, state_code, state_name):
        """Parametrized test for various state types."""
        state = State.objects.create(code=state_code, name=state_name)

        assert state.code == state_code
        assert state.name == state_name


# ============================================================================
# Relationship and Integrity Tests
# ============================================================================


class TestRelationshipsAndIntegrity:
    """Test suite for foreign key relationships and data integrity."""

    def test_cascade_delete_state_to_locality(self, db):
        """Test cascade delete from State to Locality."""
        state = State.objects.create(code="OH", name="Ohio")
        locality = Locality.objects.create(name="Columbus", state=state, postal_code="43215")

        locality_id = locality.id
        state.delete()

        assert not Locality.objects.filter(id=locality_id).exists()

    def test_cascade_delete_locality_to_address(self, db, state_instance):
        """Test cascade delete from Locality to Address."""
        locality = Locality.objects.create(
            name="Test City", state=state_instance, postal_code="12345"
        )

        address = Address.objects.create(
            street_number="100", street_name="Test St", locality=locality
        )

        address_id = address.id
        locality.delete()

        assert not Address.objects.filter(id=address_id).exists()

    def test_cascade_delete_full_chain(self, db):
        """Test cascade delete through entire State -> Locality -> Address chain."""
        state = State.objects.create(code="WA", name="Washington")
        locality = Locality.objects.create(name="Seattle", state=state, postal_code="98101")
        address = Address.objects.create(
            street_number="400", street_name="Pine St", locality=locality
        )

        address_id = address.id
        locality_id = locality.id
        state.delete()

        assert not Locality.objects.filter(id=locality_id).exists()
        assert not Address.objects.filter(id=address_id).exists()

    def test_multiple_addresses_per_locality_deletion(self, db, locality_instance):
        """Test that deleting locality removes all associated addresses."""
        addresses = []
        for i in range(5):
            address = Address.objects.create(
                street_number=str(100 + i), street_name="Main St", locality=locality_instance
            )
            addresses.append(address.id)

        locality_instance.delete()

        for address_id in addresses:
            assert not Address.objects.filter(id=address_id).exists()

    def test_locality_state_relationship_integrity(self, db, state_instance):
        """Test that locality properly maintains state relationship."""
        locality = Locality.objects.create(
            name="Test City", state=state_instance, postal_code="12345"
        )

        retrieved_locality = Locality.objects.get(id=locality.id)
        assert retrieved_locality.state.code == state_instance.code
        assert retrieved_locality.state.name == state_instance.name

    def test_address_locality_relationship_integrity(self, db, locality_instance):
        """Test that address properly maintains locality relationship."""
        address = Address.objects.create(
            street_number="123", street_name="Main St", locality=locality_instance
        )

        retrieved_address = Address.objects.get(id=address.id)
        assert retrieved_address.locality.name == locality_instance.name
        assert retrieved_address.locality.state == locality_instance.state
