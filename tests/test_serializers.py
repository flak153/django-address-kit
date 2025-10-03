"""
Comprehensive test suite for django-address-kit serializers.

This test suite aims to cover all possible scenarios for Country, State,
Locality, and Address serializers using pytest and pytest-django.
"""

import pytest
from django.core.exceptions import ValidationError

from django_address_kit.models import Country, State, Locality, Address
from django_address_kit.serializers import (
    CountrySerializer,
    StateSerializer,
    LocalitySerializer,
    AddressSerializer,
)
from rest_framework.exceptions import ValidationError as DRFValidationError


@pytest.mark.django_db
class TestCountrySerializer:
    def test_create_country_with_minimal_data(self):
        """Test creating a new country with minimal valid data."""
        serializer = CountrySerializer(data={"name": "United States", "code": "US"})
        assert serializer.is_valid()
        country = serializer.save()
        assert country.name == "United States"
        assert country.code == "US"

    def test_create_country_prevents_duplicates(self):
        """Ensure get_or_create prevents duplicate country entries."""
        # First creation
        serializer1 = CountrySerializer(data={"name": "Canada", "code": "CA"})
        assert serializer1.is_valid()
        country1 = serializer1.save()

        # Second creation with same data
        serializer2 = CountrySerializer(data={"name": "Canada", "code": "CA"})
        assert serializer2.is_valid()
        country2 = serializer2.save()

        # Should return the same country instance
        assert country1.id == country2.id

    def test_country_code_validation(self):
        """Test country code validation."""
        # Invalid country code length
        serializer = CountrySerializer(data={"name": "Test", "code": "ABC"})
        assert not serializer.is_valid()
        assert "Country code must be 2 characters" in str(serializer.errors)

    def test_update_country(self):
        """Test updating an existing country."""
        # Create initial country
        country = Country.objects.create(name="Mexico", code="MX")

        # Update via serializer
        serializer = CountrySerializer(country, data={"name": "Mexico Updated", "code": "MXN"})
        assert serializer.is_valid()
        updated_country = serializer.save()

        assert updated_country.name == "Mexico Updated"
        assert updated_country.code == "MXN"

    def test_partial_update_country(self):
        """Test partial update of a country."""
        country = Country.objects.create(name="Brazil", code="BR")

        # Partial update - only name
        serializer = CountrySerializer(country, data={"name": "Brasil"}, partial=True)
        assert serializer.is_valid()
        updated_country = serializer.save()

        assert updated_country.name == "Brasil"
        assert updated_country.code == "BR"

    def test_to_representation_format(self):
        """Test the to_representation method output format."""
        country = Country.objects.create(name="Spain", code="ES")
        serializer = CountrySerializer(country)
        data = serializer.data

        assert set(data.keys()) == {"id", "name", "code"}
        assert data["name"] == "Spain"
        assert data["code"] == "ES"

    def test_empty_name_or_code(self):
        """Test validation for empty name or code fields."""
        serializer_empty_name = CountrySerializer(data={"name": "", "code": "US"})
        assert not serializer_empty_name.is_valid()

        serializer_empty_code = CountrySerializer(data={"name": "United States", "code": ""})
        assert not serializer_empty_code.is_valid()

    def test_country_code_with_special_chars(self):
        """Test country code validation with special characters or numbers."""
        serializer_with_number = CountrySerializer(data={"name": "Invalid Country", "code": "12"})
        assert not serializer_with_number.is_valid()

        serializer_with_special_chars = CountrySerializer(data={"name": "Invalid", "code": "AB!"})
        assert not serializer_with_special_chars.is_valid()

    def test_get_or_create_with_different_codes(self):
        """Test get_or_create behavior with different codes but same name."""
        # First creation
        serializer1 = CountrySerializer(data={"name": "Test Country", "code": "TC"})
        assert serializer1.is_valid()
        country1 = serializer1.save()

        # Creation with same name but different code
        serializer2 = CountrySerializer(data={"name": "Test Country", "code": "TD"})
        assert serializer2.is_valid()
        country2 = serializer2.save()

        # Should create a different country instance
        assert country1.id != country2.id
        assert country2.code == "TD"

    def test_error_message_structure(self):
        """Verify error message format and structure."""
        invalid_data = {"name": "A" * 300, "code": "TOOLONG"}
        serializer = CountrySerializer(data=invalid_data)

        assert not serializer.is_valid()
        errors = serializer.errors

        assert "name" in errors  # Field-specific errors
        assert "code" in errors  # Field-specific errors
        assert isinstance(errors, dict)  # Ensure dictionary structure


@pytest.mark.django_db
class TestStateSerializer:
    def test_create_state_with_country(self):
        """Test creating a state with a nested country."""
        serializer = StateSerializer(
            data={
                "name": "California",
                "code": "CA",
                "country": {"name": "United States", "code": "US"},
            }
        )
        assert serializer.is_valid()
        state = serializer.save()

        assert state.name == "California"
        assert state.code == "CA"
        assert state.country.name == "United States"

    def test_create_state_prevents_duplicates(self):
        """Ensure get_or_create prevents duplicate state entries."""
        # Create country first
        country = Country.objects.create(name="United States", code="US")

        # First state creation
        serializer1 = StateSerializer(
            data={
                "name": "New York",
                "code": "NY",
                "country": {"name": "United States", "code": "US"},
            }
        )
        assert serializer1.is_valid()
        state1 = serializer1.save()

        # Second creation with same data
        serializer2 = StateSerializer(
            data={
                "name": "New York",
                "code": "NY",
                "country": {"name": "United States", "code": "US"},
            }
        )
        assert serializer2.is_valid()
        state2 = serializer2.save()

        # Should return the same state instance
        assert state1.id == state2.id

    def test_state_code_validation(self):
        """Test state code length validation."""
        country = Country.objects.create(name="United States", code="US")

        # Invalid state code length
        serializer = StateSerializer(
            data={
                "name": "Test State",
                "code": "ABCDEFGHI",
                "country": {"name": "United States", "code": "US"},
            }
        )
        assert not serializer.is_valid()
        assert "State code must be 8 characters or less" in str(serializer.errors)

    def test_update_state_with_country(self):
        """Test updating a state and its country."""
        # Create initial country and state
        country = Country.objects.create(name="Mexico", code="MX")
        state = State.objects.create(name="Baja California", code="BC", country=country)

        # Update via serializer
        serializer = StateSerializer(
            state,
            data={
                "name": "Baja California Norte",
                "code": "BCN",
                "country": {"name": "Mexico Updated", "code": "MEX"},
            },
        )
        assert serializer.is_valid()
        updated_state = serializer.save()

        assert updated_state.name == "Baja California Norte"
        assert updated_state.code == "BCN"
        assert updated_state.country.name == "Mexico Updated"
        assert updated_state.country.code == "MEX"

    def test_state_without_country(self):
        """Test creating a state with None country."""
        serializer = StateSerializer(
            data={"name": "No Country State", "code": "NC", "country": None}
        )
        assert not serializer.is_valid()
        assert "country" in serializer.errors

    def test_multiple_states_with_same_name(self):
        """Test creating states with the same name but different countries."""
        country1 = Country.objects.create(name="United States", code="US")
        country2 = Country.objects.create(name="Canada", code="CA")

        # Create first state
        serializer1 = StateSerializer(
            data={"name": "Washington", "code": "WA", "country": {"id": country1.id}}
        )
        assert serializer1.is_valid()
        state1 = serializer1.save()

        # Create second state with same name but different country
        serializer2 = StateSerializer(
            data={"name": "Washington", "code": "WA", "country": {"id": country2.id}}
        )
        assert serializer2.is_valid()
        state2 = serializer2.save()

        assert state1.country.id != state2.country.id

    def test_deserialization_from_json(self):
        """Test deserialization of state from JSON strings."""
        country = Country.objects.create(name="United States", code="US")

        serializer = StateSerializer(
            data={
                "name": str("California"),  # Explicitly using str for test
                "code": str("CA"),
                "country": {"id": country.id},
            }
        )
        assert serializer.is_valid()
        state = serializer.save()

        assert state.name == "California"
        assert state.code == "CA"

    def test_state_code_blank_or_empty(self):
        """Test behavior of state serializer with blank/empty code."""
        country = Country.objects.create(name="United States", code="US")

        serializer_blank = StateSerializer(
            data={"name": "Test State", "code": " ", "country": {"id": country.id}}
        )
        assert not serializer_blank.is_valid()
        assert "code" in serializer_blank.errors

        serializer_empty = StateSerializer(
            data={"name": "Test State", "code": "", "country": {"id": country.id}}
        )
        assert not serializer_empty.is_valid()
        assert "code" in serializer_empty.errors

    def test_nested_country_validation_failure(self):
        """Test nested country validation failures."""
        serializer = StateSerializer(
            data={
                "name": "Invalid State",
                "code": "IS",
                "country": {"name": "", "code": ""},  # Invalid nested country data
            }
        )
        assert not serializer.is_valid()
        errors = serializer.errors

        # Check for both state and nested country errors
        assert "country" in errors
        assert "name" in errors["country"]
        assert "code" in errors["country"]

    def test_read_only_fields(self):
        """Test read_only_fields behavior in StateSerializer."""
        country = Country.objects.create(name="United States", code="US")
        state = State.objects.create(name="Original", code="OG", country=country)

        # Attempt to modify read-only field if applicable
        serializer = StateSerializer(
            state,
            data={"id": 9999, "name": "Modified"},  # Attempt to change primary key
            partial=True,
        )

        assert serializer.is_valid()
        updated_state = serializer.save()

        # Ensure ID remains unchanged
        assert updated_state.id == state.id
        assert updated_state.name == "Modified"


@pytest.mark.django_db
class TestLocalitySerializer:
    def test_create_locality_with_state(self):
        """Test creating a locality with a nested state and country."""
        serializer = LocalitySerializer(
            data={
                "name": "San Francisco",
                "postal_code": "94105",
                "state": {
                    "name": "California",
                    "code": "CA",
                    "country": {"name": "United States", "code": "US"},
                },
            }
        )
        assert serializer.is_valid()
        locality = serializer.save()

        assert locality.name == "San Francisco"
        assert locality.postal_code == "94105"
        assert locality.state.name == "California"
        assert locality.state.country.name == "United States"

    def test_postal_code_validation_requires_digits(self):
        """Test postal code validation requires at least one digit."""
        # Create state first
        country = Country.objects.create(name="United States", code="US")
        state = State.objects.create(name="California", code="CA", country=country)

        # Invalid postal code without digits
        serializer = LocalitySerializer(
            data={
                "name": "San Francisco",
                "postal_code": "ABCDE",
                "state": {"name": "California", "code": "CA"},
            }
        )
        assert not serializer.is_valid()
        assert "Postal code must contain at least one number" in str(serializer.errors)

    def test_create_locality_prevents_duplicates(self):
        """Ensure get_or_create prevents duplicate locality entries."""
        # Create state first
        country = Country.objects.create(name="United States", code="US")
        state = State.objects.create(name="California", code="CA", country=country)

        # First locality creation
        serializer1 = LocalitySerializer(
            data={
                "name": "San Francisco",
                "postal_code": "94105",
                "state": {"name": "California", "code": "CA"},
            }
        )
        assert serializer1.is_valid()
        locality1 = serializer1.save()

        # Second creation with same data
        serializer2 = LocalitySerializer(
            data={
                "name": "San Francisco",
                "postal_code": "94105",
                "state": {"name": "California", "code": "CA"},
            }
        )
        assert serializer2.is_valid()
        locality2 = serializer2.save()

        # Should return the same locality instance
        assert locality1.id == locality2.id

    def test_update_locality_with_state(self):
        """Test updating a locality and its state."""
        # Create initial country, state, and locality
        country = Country.objects.create(name="United States", code="US")
        state = State.objects.create(name="California", code="CA", country=country)
        locality = Locality.objects.create(name="San Francisco", postal_code="94105", state=state)

        # Update via serializer
        serializer = LocalitySerializer(
            locality,
            data={
                "name": "San Francisco Bay Area",
                "postal_code": "94106",
                "state": {
                    "name": "California",
                    "code": "CA",
                    "country": {"name": "United States", "code": "USA"},
                },
            },
        )
        assert serializer.is_valid()
        updated_locality = serializer.save()

        assert updated_locality.name == "San Francisco Bay Area"
        assert updated_locality.postal_code == "94106"
        assert updated_locality.state.country.code == "USA"

    def test_locality_without_state(self):
        """Test creating a locality with None state."""
        serializer = LocalitySerializer(
            data={"name": "Stateless City", "postal_code": "12345", "state": None}
        )
        assert not serializer.is_valid()
        assert "state" in serializer.errors

    def test_postal_codes_with_only_special_chars(self):
        """Test postal code validation with special characters."""
        country = Country.objects.create(name="United States", code="US")
        state = State.objects.create(name="California", code="CA", country=country)

        serializer_special_chars = LocalitySerializer(
            data={
                "name": "Test Locality",
                "postal_code": "-----",
                "state": {"name": "California", "code": "CA"},
            }
        )
        assert not serializer_special_chars.is_valid()
        assert "Postal code must contain at least one number" in str(
            serializer_special_chars.errors
        )

    def test_international_postal_codes(self):
        """Test support for international postal code formats."""
        country = Country.objects.create(name="United Kingdom", code="GB")
        state = State.objects.create(name="Greater London", code="LDN", country=country)

        # Alphanumeric postal code
        serializer_uk = LocalitySerializer(
            data={
                "name": "London",
                "postal_code": "SW1A 1AA",  # UK postal code format
                "state": {"name": "Greater London", "code": "LDN"},
            }
        )
        assert serializer_uk.is_valid()
        locality_uk = serializer_uk.save()

        assert locality_uk.name == "London"
        assert locality_uk.postal_code == "SW1A 1AA"

    def test_very_long_locality_names(self):
        """Test handling of extremely long locality names."""
        country = Country.objects.create(name="United States", code="US")
        state = State.objects.create(name="California", code="CA", country=country)

        # 500+ character locality name
        long_name = "A" * 501

        serializer = LocalitySerializer(
            data={
                "name": long_name,
                "postal_code": "94105",
                "state": {"name": "California", "code": "CA"},
            }
        )
        assert not serializer.is_valid()
        assert "name" in serializer.errors

    def test_multiple_localities_same_name(self):
        """Test creating localities with the same name in different states."""
        country1 = Country.objects.create(name="United States", code="US")
        country2 = Country.objects.create(name="Canada", code="CA")

        state1 = State.objects.create(name="California", code="CA", country=country1)
        state2 = State.objects.create(name="Ontario", code="ON", country=country2)

        # First locality
        serializer1 = LocalitySerializer(
            data={
                "name": "Springfield",
                "postal_code": "12345",
                "state": {"name": "California", "code": "CA"},
            }
        )
        assert serializer1.is_valid()
        locality1 = serializer1.save()

        # Second locality with same name but different state
        serializer2 = LocalitySerializer(
            data={
                "name": "Springfield",
                "postal_code": "54321",
                "state": {"name": "Ontario", "code": "ON"},
            }
        )
        assert serializer2.is_valid()
        locality2 = serializer2.save()

        assert locality1.state.id != locality2.state.id

    def test_partial_update_nested_state(self):
        """Test partial update of a locality with nested state update."""
        country = Country.objects.create(name="United States", code="US")
        state = State.objects.create(name="California", code="CA", country=country)
        locality = Locality.objects.create(name="Original City", postal_code="94105", state=state)

        # Partial update with nested state
        serializer = LocalitySerializer(
            locality, data={"state": {"name": "Modified California", "code": "CA"}}, partial=True
        )

        assert serializer.is_valid()
        updated_locality = serializer.save()

        assert updated_locality.state.name == "Modified California"
        assert updated_locality.name == "Original City"  # Ensure original name unchanged


@pytest.mark.django_db
class TestAddressSerializer:
    def test_create_address_with_full_data(self):
        """Test creating an address with full nested data."""
        serializer = AddressSerializer(
            data={
                "raw": "123 Main St, San Francisco, CA 94105",
                "street_number": "123",
                "route": "Main St",
                "locality": {
                    "name": "San Francisco",
                    "postal_code": "94105",
                    "state": {
                        "name": "California",
                        "code": "CA",
                        "country": {"name": "United States", "code": "US"},
                    },
                },
                "latitude": 37.7749,
                "longitude": -122.4194,
                "formatted": "123 Main St, San Francisco, CA 94105, USA",
            }
        )
        assert serializer.is_valid()
        address = serializer.save()

        assert address.raw == "123 Main St, San Francisco, CA 94105"
        assert address.street_number == "123"
        assert address.route == "Main St"
        assert address.locality.name == "San Francisco"
        assert address.locality.postal_code == "94105"
        assert address.locality.state.name == "California"
        assert address.latitude == 37.7749
        assert address.longitude == -122.4194

    def test_validate_raw_address_not_empty(self):
        """Test raw address cannot be empty."""
        serializer = AddressSerializer(data={"raw": "", "street_number": "123", "route": "Main St"})
        assert not serializer.is_valid()
        assert "Raw address cannot be empty" in str(serializer.errors)

    def test_create_address_with_minimal_data(self):
        """Test creating an address with only the required raw field."""
        serializer = AddressSerializer(data={"raw": "123 Main St, Anytown, USA"})
        assert serializer.is_valid()
        address = serializer.save()

        assert address.raw == "123 Main St, Anytown, USA"
        assert address.locality is None

    def test_update_address_with_partial_data(self):
        """Test updating an address with partial data."""
        # First create an address
        initial_address = Address.objects.create(
            raw="123 Main St, San Francisco, CA 94105", street_number="123", route="Main St"
        )

        # Update via serializer
        serializer = AddressSerializer(
            initial_address,
            data={
                "raw": "456 Market St, San Francisco, CA 94105",
                "street_number": "456",
                "route": "Market St",
            },
            partial=True,
        )

        assert serializer.is_valid()
        updated_address = serializer.save()

        assert updated_address.raw == "456 Market St, San Francisco, CA 94105"
        assert updated_address.street_number == "456"
        assert updated_address.route == "Market St"

    def test_address_with_special_characters(self):
        """Test addresses with special characters and complex formatting."""
        serializer = AddressSerializer(
            data={
                "raw": "123 Áéíóú St, San José, CA 95110",
                "street_number": "123",
                "route": "Áéíóú St",
                "locality": {
                    "name": "San José",
                    "postal_code": "95110",
                    "state": {
                        "name": "California",
                        "code": "CA",
                        "country": {"name": "United States", "code": "US"},
                    },
                },
            }
        )
        assert serializer.is_valid()
        address = serializer.save()

        assert address.raw == "123 Áéíóú St, San José, CA 95110"
        assert address.route == "Áéíóú St"
        assert address.locality.name == "San José"

    def test_edge_cases_with_none_and_empty_values(self):
        """Test various edge cases with None and empty values."""
        # Test different combinations of None and empty values
        test_cases = [
            # Minimal required data
            {"raw": "123 Main St"},
            # None or empty street details
            {"raw": "123 Main St", "street_number": None, "route": ""},
            # Empty locality
            {"raw": "123 Main St", "locality": None},
            # Geocoding fields
            {"raw": "123 Main St", "latitude": None, "longitude": 0.0},
        ]

        for case in test_cases:
            serializer = AddressSerializer(data=case)
            assert serializer.is_valid(), f"Failed for case: {case}"
            address = serializer.save()
            assert address.raw == case["raw"]
