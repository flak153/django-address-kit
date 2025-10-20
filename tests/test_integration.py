import pytest

from django_address_kit import models
from tests import factories


@pytest.mark.django_db
def test_select_related_minimizes_queries(django_assert_num_queries, faker):
    country = factories.create_country(faker, code="US", name="United States")
    state = factories.create_state(faker, country=country, name="California", code="CA")
    locality = factories.create_locality(
        faker, state=state, name="San Francisco", postal_code="94102"
    )
    factories.create_address(
        faker,
        locality=locality,
        street_number="100",
        street_name="First",
        street_type="Street",
    )
    factories.create_address(
        faker,
        locality=locality,
        street_number="200",
        street_name="Second",
        street_type="Street",
    )

    with django_assert_num_queries(1):
        addresses = list(
            models.Address.objects.select_related("locality__state__country").order_by("id")
        )

    assert len(addresses) == 2
