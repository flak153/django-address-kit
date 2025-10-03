"""
Comprehensive test suite for Django Address Kit serializer validation.

This test module covers:
1. Field-level validators
2. Cross-field validation
3. Nested serializer validation
4. DRF field options
5. Custom validation logic
6. Validation error formats
7. Boundary cases
8. Integration validation
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework import serializers

from django_address_kit.models import Country, State, Locality, Address
from django_address_kit.serializers import (
    CountrySerializer,
    StateSerializer,
    LocalitySerializer,
    AddressSerializer,
)


@pytest.mark.django_db
class TestSerializerValidation:
    """
    Comprehensive serializer validation test suite.

    Covers various validation scenarios across different serializers.
    """

    # 1. Field-Level Validators
    def test_country_code_validator(self):
        """Test country code validation."""
        # Invalid country code length
        with pytest.raises(serializers.ValidationError, match="Country code must be 2 characters"):
            serializer = CountrySerializer(data={"name": "Test Country", "code": "USA"})
            serializer.is_valid(raise_exception=True)

        # Valid country code
        serializer = CountrySerializer(data={"name": "United States", "code": "US"})
        assert serializer.is_valid(), serializer.errors

    def test_state_code_validator(self):
        """Test state code validation."""
        # Too long state code
        with pytest.raises(
            serializers.ValidationError, match="State code must be 8 characters or less"
        ):
            serializer = StateSerializer(data={"name": "Test State", "code": "TOOLONGSTATECODE"})
            serializer.is_valid(raise_exception=True)

        # Valid state code
        serializer = StateSerializer(data={"name": "California", "code": "CA"})
        assert serializer.is_valid(), serializer.errors

    def test_locality_postal_code_validator(self):
        """Test postal code validation for localities."""
        # Postal code without digits
        with pytest.raises(
            serializers.ValidationError, match="Postal code must contain at least one number"
        ):
            serializer = LocalitySerializer(data={"name": "Test City", "postal_code": "NODIGITS"})
            serializer.is_valid(raise_exception=True)

        # Valid postal code
        serializer = LocalitySerializer(data={"name": "Springfield", "postal_code": "62701"})
        assert serializer.is_valid(), serializer.errors

    def test_address_raw_validator(self):
        """Test raw address validation."""
        # Empty raw address
        with pytest.raises(serializers.ValidationError, match="Raw address cannot be empty"):
            serializer = AddressSerializer(data={"raw": "   "})
            serializer.is_valid(raise_exception=True)

        # Valid raw address
        serializer = AddressSerializer(data={"raw": "123 Main St, Springfield, IL 62701"})
        assert serializer.is_valid(), serializer.errors

    # 2. Nested Serializer Validation
    def test_nested_serializer_validation(self):
        """Test validation propagation through nested serializers."""
        # Invalid nested country code
        with pytest.raises(serializers.ValidationError):
            serializer = StateSerializer(
                data={
                    "name": "Test State",
                    "code": "CA",
                    "country": {"name": "Test Country", "code": "INVALID"},
                }
            )
            serializer.is_valid(raise_exception=True)

        # Valid nested serializer
        serializer = StateSerializer(
            data={
                "name": "California",
                "code": "CA",
                "country": {"name": "United States", "code": "US"},
            }
        )
        assert serializer.is_valid(), serializer.errors

    # 3. DRF Field Options
    def test_field_options(self):
        """Test various DRF field options."""
        # Required field
        with pytest.raises(serializers.ValidationError):
            serializer = CountrySerializer(data={})
            serializer.is_valid(raise_exception=True)

        # Optional nested field with None
        serializer = AddressSerializer(data={"raw": "123 Main St", "locality": None})
        assert serializer.is_valid(), serializer.errors

    # 4. Custom Validation Logic
    @pytest.mark.parametrize(
        "invalid_data, error_msg",
        [
            # Invalid country code
            ({"name": "Test Country", "code": "USA"}, "Country code must be 2 characters"),
            # Invalid state code length
            (
                {"name": "Test State", "code": "TOOLONGCODE"},
                "State code must be 8 characters or less",
            ),
            # Postal code without digits
            (
                {"name": "Test City", "postal_code": "NODIGITS"},
                "Postal code must contain at least one number",
            ),
        ],
    )
    def test_custom_validation_cases(self, invalid_data, error_msg):
        """Test various custom validation scenarios."""
        serializer_classes = [CountrySerializer, StateSerializer, LocalitySerializer]

        for serializer_cls in serializer_classes:
            with pytest.raises(serializers.ValidationError, match=error_msg):
                serializer = serializer_cls(data=invalid_data)
                serializer.is_valid(raise_exception=True)

    # 5. Validation Error Formats
    def test_multiple_validation_errors(self):
        """Test multiple validation errors in a single serializer."""
        serializer = CountrySerializer(
            data={"name": "", "code": "USA"}  # Missing name  # Invalid code
        )

        assert not serializer.is_valid()
        assert len(serializer.errors) > 1
        assert "name" in serializer.errors
        assert "code" in serializer.errors

    # 6. Boundary Cases
    @pytest.mark.parametrize(
        "field_data",
        [
            # Max length tests
            {"name": "A" * 255, "code": "US"},  # Very long name
            {"name": "Test Country", "code": "A" * 10},  # Code too long
        ],
    )
    def test_field_length_boundaries(self, field_data):
        """Test field length boundaries."""
        with pytest.raises(serializers.ValidationError):
            serializer = CountrySerializer(data=field_data)
            serializer.is_valid(raise_exception=True)

    # 7. Integration Validation
    def test_uniqueness_validation(self):
        """Test database-level uniqueness validation."""
        # Create first country
        Country.objects.create(name="United States", code="US")

        # Try to create duplicate country
        with pytest.raises(IntegrityError):
            Country.objects.create(name="United States", code="US")

    # Additional Complex Nested Validation Scenario
    def test_complex_nested_address_validation(self):
        """Test complex nested address validation with multiple levels."""
        serializer = AddressSerializer(
            data={
                "raw": "123 Main St, Springfield, IL 62701",
                "street_number": "123",
                "route": "Main St",
                "locality": {
                    "name": "Springfield",
                    "postal_code": "62701",
                    "state": {
                        "name": "Illinois",
                        "code": "IL",
                        "country": {"name": "United States", "code": "US"},
                    },
                },
            }
        )

        # Validate entire nested structure
        assert serializer.is_valid(), serializer.errors
