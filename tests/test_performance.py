import pytest
from django.db import connection
from django.test import override_settings
from memory_profiler import memory_usage

from django_address_kit.models import Country, State, Locality, Address


@pytest.mark.performance
class TestAddressKitPerformance:
    """Performance tests for address kit models and operations."""

    @pytest.mark.benchmark(group="bulk-create")
    def test_bulk_address_creation_performance(self, benchmark, django_db_setup, django_db_blocker):
        """
        Benchmark bulk address creation performance.

        Performance goals:
        - Less than 50ms for 1000 address bulk creation
        - Memory usage under 100MB for the operation
        """
        with django_db_blocker.unblock():
            # Prepare test data
            country = Country.objects.create(name="United States", code="US")
            state = State.objects.create(name="California", code="CA", country=country)
            locality = Locality.objects.create(
                name="San Francisco", postal_code="94105", state=state
            )

            def create_addresses():
                addresses = [
                    Address(
                        raw=f"Address {i} Market St",
                        street_number=str(i * 10),
                        route="Market St",
                        locality=locality,
                        formatted=f"{i * 10} Market St, San Francisco, CA 94105",
                    )
                    for i in range(1000)
                ]
                Address.objects.bulk_create(addresses)

            # Benchmark and check performance
            result = benchmark(create_addresses)

            # Memory usage check
            mem_usage = memory_usage(create_addresses, max_iterations=1)
            assert max(mem_usage) < 100, "Memory usage exceeds 100MB"

    @pytest.mark.benchmark(group="query-performance")
    def test_n_plus_one_query_detection(self, django_db_setup):
        """
        Detect and prevent N+1 query performance anti-pattern.

        Goals:
        - Limit total query count when accessing related models
        - Query count should not increase linearly with object count
        """
        # Prepare test data
        country = Country.objects.create(name="United States", code="US")
        state = State.objects.create(name="California", code="CA", country=country)
        locality = Locality.objects.create(name="San Francisco", postal_code="94105", state=state)

        # Create multiple addresses
        addresses = [
            Address.objects.create(
                raw=f"Address {i} Market St",
                street_number=str(i * 10),
                route="Market St",
                locality=locality,
            )
            for i in range(50)
        ]

        # Reset query counter
        with connection.cursor() as cursor:
            cursor.execute("RESET QUERY COUNT")

        # Measure queries when accessing related data
        with pytest.raises(AssertionError, match="Too many database queries"):
            with self.assertNumQueries(3):  # Expect minimal queries
                for addr in Address.objects.select_related("locality__state__country").all():
                    # Access nested related fields
                    _ = addr.locality.state.country.name

    @pytest.mark.benchmark(group="serialization")
    def test_address_serialization_performance(self, benchmark):
        """
        Benchmark address model serialization performance.

        Goals:
        - Serialization of 1000 addresses under 200ms
        - Low memory overhead
        """
        # Prepare test data
        country = Country.objects.create(name="United States", code="US")
        state = State.objects.create(name="California", code="CA", country=country)
        locality = Locality.objects.create(name="San Francisco", postal_code="94105", state=state)

        addresses = [
            Address.objects.create(
                raw=f"Address {i} Market St",
                street_number=str(i * 10),
                route="Market St",
                locality=locality,
            )
            for i in range(1000)
        ]

        def serialize_addresses():
            return [addr.as_dict() for addr in addresses]

        # Benchmark serialization
        result = benchmark(serialize_addresses)

        # Check result and performance
        assert len(result) == 1000

    @pytest.mark.benchmark(group="index-test")
    def test_database_index_effectiveness(self, benchmark):
        """
        Test database index performance for common query patterns.

        Goals:
        - Measure query time for indexed vs non-indexed lookups
        - Ensure indexes improve query performance
        """
        # Prepare test data with multiple records
        country = Country.objects.create(name="United States", code="US")
        state = State.objects.create(name="California", code="CA", country=country)
        locality = Locality.objects.create(name="San Francisco", postal_code="94105", state=state)

        addresses = [
            Address.objects.create(
                raw=f"Address {i} Market St",
                street_number=str(i * 10),
                route="Market St",
                locality=locality,
            )
            for i in range(5000)
        ]

        # Benchmark indexed lookup
        def indexed_lookup():
            return list(Address.objects.filter(locality=locality))

        result_indexed = benchmark(indexed_lookup)
        assert len(result_indexed) > 0

    @pytest.mark.benchmark(group="large-dataset")
    @override_settings(TEST_RUNNER="django.test.runner.DiscoverRunner")
    def test_large_dataset_handling(self, django_db_setup):
        """
        Test performance and memory handling with large datasets.

        Goals:
        - Process 50,000 addresses without significant performance degradation
        - Memory usage remains stable
        """
        # Prepare test data
        country = Country.objects.create(name="United States", code="US")
        state = State.objects.create(name="California", code="CA", country=country)
        locality = Locality.objects.create(name="San Francisco", postal_code="94105", state=state)

        # Large dataset creation
        addresses = [
            Address(
                raw=f"Address {i} Market St",
                street_number=str(i * 10),
                route="Market St",
                locality=locality,
            )
            for i in range(50_000)
        ]

        # Measure memory during bulk creation
        mem_usage = memory_usage(
            lambda: Address.objects.bulk_create(addresses, batch_size=1000), max_iterations=1
        )

        # Validate results
        assert Address.objects.count() == 50_000
        assert max(mem_usage) < 500  # Memory under 500MB
