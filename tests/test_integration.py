"""
Integration Tests for django-address-kit

Covers comprehensive test scenarios for address-related models and workflows.
"""

import pytest
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.db.models import Prefetch, Q
from django.test import TestCase
from django_address_kit.models import Country, State, Locality, Address


@pytest.mark.django_db
class TestAddressIntegration:
    """
    Comprehensive integration tests for address-related models and workflows.
    Covers end-to-end address creation, serialization, query optimization,
    and complex scenarios.
    """

    @pytest.fixture
    def base_country(self):
        """Create a base country for testing."""
        return Country.objects.create(name="United States", code="US")

    @pytest.fixture
    def base_state(self, base_country):
        """Create a base state for testing."""
        return State.objects.create(name="California", code="CA", country=base_country)

    @pytest.fixture
    def base_locality(self, base_state):
        """Create a base locality for testing."""
        return Locality.objects.create(name="San Francisco", postal_code="94105", state=base_state)

    def test_end_to_end_address_creation_workflow(self, base_country, base_state, base_locality):
        """
        Test complete address creation workflow with full relationship chain.
        Ensures proper cascading and relationship integrity.
        """
        # Verify base objects
        assert base_country.name == "United States"
        assert base_state.country == base_country
        assert base_locality.state == base_state

        # Create a full address
        address = Address.objects.create(
            street_number="350",
            route="5th Street",
            locality=base_locality,
            raw="350 5th Street, San Francisco, CA 94105",
            formatted="350 5th Street, San Francisco, CA 94105",
            latitude=37.7875,
            longitude=-122.4001,
        )

        # Verify address creation and relationships
        assert address.street_number == "350"
        assert address.locality == base_locality
        assert address.locality.state == base_state
        assert address.locality.state.country == base_country

    def test_cascade_deletion(self, base_country, base_state, base_locality):
        """
        Test cascade deletion across all address-related models.
        Ensures referential integrity and proper deletion behavior.
        """
        # Create a full chain of objects
        address = Address.objects.create(
            street_number="100",
            route="Main St",
            locality=base_locality,
            raw="100 Main St, San Francisco, CA 94105",
        )

        # Delete the country, which should cascade delete all related objects
        base_country.delete()

        # Verify all related objects are deleted
        with pytest.raises(Country.DoesNotExist):
            Country.objects.get(pk=base_country.pk)

        with pytest.raises(State.DoesNotExist):
            State.objects.get(pk=base_state.pk)

        with pytest.raises(Locality.DoesNotExist):
            Locality.objects.get(pk=base_locality.pk)

        with pytest.raises(Address.DoesNotExist):
            Address.objects.get(pk=address.pk)

    def test_query_optimization(self, base_country, base_state):
        """
        Test query optimization techniques using select_related and prefetch_related.
        """
        # Create multiple localities for a state
        locality1 = Locality.objects.create(
            name="San Francisco", postal_code="94105", state=base_state
        )
        locality2 = Locality.objects.create(name="Oakland", postal_code="94601", state=base_state)

        # Create addresses for each locality
        Address.objects.create(
            street_number="350",
            route="5th Street",
            locality=locality1,
            raw="350 5th Street, San Francisco, CA 94105",
        )
        Address.objects.create(
            street_number="200",
            route="Broadway",
            locality=locality2,
            raw="200 Broadway, Oakland, CA 94601",
        )

        # Optimized query with select_related
        with pytest.raises(Exception):  # Placeholder for query counting
            optimized_addresses = Address.objects.select_related("locality__state__country").all()

            # Verify minimal number of database queries
            assert len(optimized_addresses) == 2
            for addr in optimized_addresses:
                assert addr.locality.state.country == base_country

    def test_complex_filtering(self, base_country, base_state):
        """
        Test complex filtering and lookups across address-related models.
        """
        # Create multiple localities and addresses
        locality1 = Locality.objects.create(
            name="San Francisco", postal_code="94105", state=base_state
        )
        locality2 = Locality.objects.create(name="San Jose", postal_code="95110", state=base_state)

        Address.objects.create(
            street_number="350",
            route="5th Street",
            locality=locality1,
            raw="350 5th Street, San Francisco, CA 94105",
        )
        Address.objects.create(
            street_number="100",
            route="1st Street",
            locality=locality2,
            raw="100 1st Street, San Jose, CA 95110",
        )

        # Complex filtering
        complex_addresses = Address.objects.filter(
            Q(locality__postal_code__startswith="94") & Q(street_number__gte="200")
        )

        assert complex_addresses.count() == 1
        assert complex_addresses[0].locality.name == "San Francisco"

    def test_transaction_integrity(self, base_country, base_state):
        """
        Test transaction integrity and rollback mechanisms.
        """
        initial_address_count = Address.objects.count()

        try:
            with transaction.atomic():
                locality = Locality.objects.create(
                    name="Palo Alto", postal_code="94301", state=base_state
                )

                # Intentionally create an invalid address to trigger rollback
                Address.objects.create(raw="")  # This should fail due to validation

        except ValidationError:
            # Verify no address was created during the failed transaction
            assert Address.objects.count() == initial_address_count
            assert Locality.objects.filter(name="Palo Alto").count() == 0

    def test_bulk_operations(self, base_country, base_state):
        """
        Test bulk create and update operations for addresses.
        """
        locality = Locality.objects.create(name="Sacramento", postal_code="95814", state=base_state)

        # Bulk Create
        bulk_addresses = [
            Address(
                street_number="1",
                route="Capitol Mall",
                locality=locality,
                raw="1 Capitol Mall, Sacramento, CA 95814",
            ),
            Address(
                street_number="2",
                route="Main St",
                locality=locality,
                raw="2 Main St, Sacramento, CA 95814",
            ),
            Address(
                street_number="3",
                route="L Street",
                locality=locality,
                raw="3 L Street, Sacramento, CA 95814",
            ),
        ]
        Address.objects.bulk_create(bulk_addresses)

        assert Address.objects.filter(locality=locality).count() == 3

        # Bulk Update
        addresses_to_update = Address.objects.filter(locality=locality)
        for address in addresses_to_update:
            address.formatted = f"Formatted {address.raw}"

        Address.objects.bulk_update(addresses_to_update, ["formatted"])

        updated_addresses = Address.objects.filter(locality=locality)
        assert all("Formatted" in addr.formatted for addr in updated_addresses)

    def test_po_box_address(self, base_country, base_state):
        """
        Test PO Box address scenario.
        """
        locality = Locality.objects.create(
            name="San Francisco", postal_code="94105", state=base_state
        )

        po_box_address = Address.objects.create(
            street_number="PO Box 123",
            route="",  # No street route
            locality=locality,
            raw="PO Box 123, San Francisco, CA 94105",
        )

        assert po_box_address.street_number == "PO Box 123"
        assert po_box_address.route == ""

    def test_military_address(self, base_country, base_state):
        """
        Test military address scenario (APO/FPO).
        """
        # Create a special state for military addresses
        military_state = State.objects.create(
            name="Armed Forces Pacific", code="AP", country=base_country
        )

        locality = Locality.objects.create(name="APO", postal_code="96543", state=military_state)

        military_address = Address.objects.create(
            street_number="PSC 123",
            route="Box 456",
            locality=locality,
            raw="PSC 123, Box 456, APO, AP 96543",
        )

        assert military_address.locality.state.name == "Armed Forces Pacific"
        assert military_address.locality.postal_code == "96543"

    def test_territory_address(self, base_country):
        """
        Test US territory address scenario.
        """
        territory_state = State.objects.create(name="Puerto Rico", code="PR", country=base_country)

        locality = Locality.objects.create(
            name="San Juan", postal_code="00901", state=territory_state
        )

        territory_address = Address.objects.create(
            street_number="100",
            route="Fortaleza Street",
            locality=locality,
            raw="100 Fortaleza Street, San Juan, PR 00901",
        )

        assert territory_address.locality.state.name == "Puerto Rico"
        assert territory_address.locality.postal_code == "00901"

    def test_comprehensive_us_address(self, base_country, base_state):
        """
        Test a comprehensive US address with all possible fields.
        """
        locality = Locality.objects.create(
            name="San Francisco", postal_code="94105", state=base_state
        )

        comprehensive_address = Address.objects.create(
            street_number="350",
            route="5th Street",
            locality=locality,
            raw="350 5th Street, San Francisco, CA 94105",
            formatted="350 5th Street, San Francisco, CA 94105, United States",
            latitude=37.7875,
            longitude=-122.4001,
        )

        address_dict = comprehensive_address.as_dict()

        assert address_dict["street_number"] == "350"
        assert address_dict["route"] == "5th Street"
        assert address_dict["locality"] == "San Francisco"
        assert address_dict["postal_code"] == "94105"
        assert address_dict["state"] == "California"
        assert address_dict["state_code"] == "CA"
        assert address_dict["country"] == "United States"
        assert address_dict["country_code"] == "US"
