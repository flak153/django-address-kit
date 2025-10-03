import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.db import transaction
from concurrent.futures import ThreadPoolExecutor

from django_address_kit.models import Country, State, Locality, Address


@pytest.mark.edge_case
class TestAddressKitEdgeCases:
    """Edge case and security tests for django-address-kit."""

    @pytest.mark.parametrize(
        "test_input",
        [
            "伍佰街道",  # Chinese characters
            "渋谷区東京都",  # Japanese address
            "Рижский проспект",  # Russian address
            "🏠 Address with emoji",  # Emoji in address
            "حي النهضة",  # Arabic address
        ],
    )
    def test_unicode_and_international_characters(self, django_db_setup, test_input):
        """
        Test handling of Unicode and international characters in address fields.

        Validate:
        - Unicode characters are preserved
        - No encoding errors
        - Proper string handling across different scripts
        """
        country = Country.objects.create(name="International Test", code="XX")
        state = State.objects.create(name="Unicode State", code="UN", country=country)
        locality = Locality.objects.create(name="Unicode City", postal_code="12345", state=state)

        # Test raw and formatted fields with Unicode
        address = Address.objects.create(
            raw=test_input,
            street_number="123",
            route=test_input,
            locality=locality,
            formatted=test_input,
        )

        assert address.raw == test_input
        assert address.route == test_input
        assert address.formatted == test_input

    def test_very_long_field_values(self, django_db_setup):
        """
        Test behavior with extremely long field inputs.

        Goals:
        - Validate truncation or validation for field length limits
        - Ensure no data corruption or unexpected behavior
        """
        long_street = "A" * 150  # Exceeds max route length
        long_raw = "B" * 250  # Exceeds max raw address length

        country = Country.objects.create(name="LongFieldTest", code="LF")
        state = State.objects.create(name="Long Field State", code="LFS", country=country)
        locality = Locality.objects.create(name="Long Field City", postal_code="98765", state=state)

        with pytest.raises(ValidationError):
            Address.objects.create(
                raw=long_raw, street_number="999", route=long_street, locality=locality
            )

    @pytest.mark.parametrize(
        "special_chars",
        ["!@#$%^&*()_+", "<script>alert('XSS')</script>", "\\' OR 1=1 --", "SELECT * FROM Users;"],
    )
    def test_special_characters_and_injection_attempts(self, django_db_setup, special_chars):
        """
        Test handling of special characters and potential injection attempts.

        Goals:
        - Prevent SQL injection
        - Sanitize or escape dangerous inputs
        - Maintain data integrity
        """
        country = Country.objects.create(name=f"Test Country {special_chars}", code="TC")
        state = State.objects.create(name=f"Test State {special_chars}", code="TS", country=country)
        locality = Locality.objects.create(
            name=f"Test City {special_chars}", postal_code="12345", state=state
        )

        # Create address with special characters
        address = Address.objects.create(
            raw=f"Test Address {special_chars}",
            street_number=special_chars,
            route=special_chars,
            locality=locality,
        )

        # Verify data is stored as-is without causing errors
        assert address.street_number == special_chars
        assert address.route == special_chars

    def test_concurrent_address_creation(self, django_db_setup):
        """
        Test concurrent access and creation of address-related models.

        Goals:
        - Validate thread safety
        - Prevent race conditions
        - Ensure data consistency under parallel access
        """
        country = Country.objects.create(name="Concurrent Test", code="CT")
        state = State.objects.create(name="Concurrent State", code="CS", country=country)
        locality = Locality.objects.create(name="Concurrent City", postal_code="54321", state=state)

        def create_address(index):
            with transaction.atomic():
                return Address.objects.create(
                    raw=f"Concurrent Address {index}",
                    street_number=str(index),
                    route=f"Concurrent St {index}",
                    locality=locality,
                )

        # Simulate 50 concurrent address creations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_address, i) for i in range(50)]

            # Wait for all tasks to complete
            results = [future.result() for future in futures]

        # Verify all addresses were created successfully
        assert Address.objects.filter(locality=locality).count() == 50

    def test_empty_and_null_value_combinations(self, django_db_setup):
        """
        Test various combinations of empty and null values.

        Goals:
        - Validate model validation
        - Ensure graceful handling of partially filled data
        - Test edge cases in nullable/blank fields
        """
        country = Country.objects.create(name="Empty Value Test", code="EV")
        state = State.objects.create(name="Empty State", code="ES", country=country)
        locality = Locality.objects.create(name="Empty City", postal_code="", state=state)

        # Test with completely minimal data
        with pytest.raises(ValidationError, match="Addresses may not have a blank `raw` field"):
            Address.objects.create(
                raw="",  # Explicitly test raw field validation
                street_number="",
                route="",
                locality=None,
            )

        # Test with some fields empty, some null
        address = Address.objects.create(
            raw="Minimal Test Address", street_number="", route=None, locality=None, formatted=""
        )

        assert address.street_number == ""
        assert address.route is None
        assert address.locality is None

    def test_invalid_foreign_key_references(self, django_db_setup):
        """
        Test behavior with invalid foreign key references.

        Goals:
        - Prevent creation of addresses with non-existent foreign keys
        - Validate cascading delete behaviors
        - Ensure data integrity
        """
        # Attempt to create an address with a non-existent locality
        with pytest.raises((ValidationError, ValueError)):
            Address.objects.create(
                raw="Invalid Foreign Key Address",
                street_number="404",
                route="Not Found Street",
                locality_id=9999,  # Non-existent locality ID
            )

        # Create a country and state to demonstrate cascading delete
        country = Country.objects.create(name="Cascade Test", code="CT")
        state = State.objects.create(name="Cascade State", code="CS", country=country)
        locality = Locality.objects.create(name="Cascade City", postal_code="12345", state=state)

        # Create an address
        address = Address.objects.create(
            raw="Cascade Test Address",
            street_number="100",
            route="Cascade Street",
            locality=locality,
        )

        # Delete related state, should cascade and delete address
        state.delete()

        # Verify address is also deleted
        with pytest.raises(Address.DoesNotExist):
            Address.objects.get(pk=address.pk)
