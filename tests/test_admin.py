import pytest
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse

from django_address_kit.models import Country, State, Locality, Address
from django_address_kit.admin import (
    CountryAdmin,
    StateAdmin,
    LocalityAdmin,
    AddressAdmin,
)

User = get_user_model()


@pytest.mark.django_db
class TestAddressKitAdmin:
    """Comprehensive test suite for Django Address Kit admin."""

    @pytest.fixture
    def admin_site(self):
        """Create a mock admin site."""
        return AdminSite()

    @pytest.fixture
    def admin_user(self):
        """Create a superuser for admin tests."""
        return User.objects.create_superuser(
            username="admin", email="admin@example.com", password="testpass123"
        )

    @pytest.fixture
    def request_factory(self):
        """Create a request factory for testing."""
        return RequestFactory()

    def test_country_admin_registration(self):
        """Test that Country model is registered in admin."""
        assert admin.site._registry[Country].__class__.__name__ == "CountryAdmin"

    def test_state_admin_registration(self):
        """Test that State model is registered in admin."""
        assert admin.site._registry[State].__class__.__name__ == "StateAdmin"

    def test_locality_admin_registration(self):
        """Test that Locality model is registered in admin."""
        assert admin.site._registry[Locality].__class__.__name__ == "LocalityAdmin"

    def test_address_admin_registration(self):
        """Test that Address model is registered in admin."""
        assert admin.site._registry[Address].__class__.__name__ == "AddressAdmin"

    def test_country_admin_list_display(self, admin_site):
        """Test CountryAdmin list display fields."""
        country_admin = CountryAdmin(Country, admin_site)
        assert country_admin.list_display == ("name", "code")

    def test_country_admin_search_fields(self, admin_site):
        """Test CountryAdmin search fields."""
        country_admin = CountryAdmin(Country, admin_site)
        assert country_admin.search_fields == ("name", "code")

    def test_country_admin_list_filter(self, admin_site):
        """Test CountryAdmin list filter."""
        country_admin = CountryAdmin(Country, admin_site)
        assert country_admin.list_filter == ("name",)

    def test_state_admin_inlines(self, admin_site):
        """Test that StateAdmin has proper inline configuration."""
        state_admin = StateAdmin(State, admin_site)
        assert len(state_admin.inlines) == 1
        assert state_admin.inlines[0].__name__ == "LocalityInline"

    def test_address_admin_readonly_fields(self, admin_user, admin_site, request_factory):
        """Test that latitude and longitude are read-only for non-superusers."""
        request = request_factory.get("/admin")
        request.user = admin_user

        address_admin = AddressAdmin(Address, admin_site)
        readonly_fields = address_admin.get_readonly_fields(request)
        assert "formatted" in readonly_fields

    def test_address_admin_readonly_fields_with_non_superuser(self, admin_site, request_factory):
        """Test that non-superusers have more read-only fields."""
        non_super_user = User.objects.create_user(username="regular_user", password="testpass123")
        request = request_factory.get("/admin")
        request.user = non_super_user

        address_admin = AddressAdmin(Address, admin_site)
        readonly_fields = address_admin.get_readonly_fields(request)
        assert "formatted" in readonly_fields
        assert "latitude" in readonly_fields
        assert "longitude" in readonly_fields

    def test_address_admin_search_fields(self, admin_site):
        """Test AddressAdmin search fields cover various related fields."""
        address_admin = AddressAdmin(Address, admin_site)
        expected_search_fields = (
            "raw",
            "formatted",
            "street_number",
            "route",
            "locality__name",
            "locality__postal_code",
            "locality__state__name",
        )
        assert address_admin.search_fields == expected_search_fields

    def test_address_admin_list_display(self, admin_site):
        """Test AddressAdmin list display fields."""
        address_admin = AddressAdmin(Address, admin_site)
        expected_list_display = (
            "__str__",
            "street_number",
            "route",
            "locality",
            "latitude",
            "longitude",
        )
        assert address_admin.list_display == expected_list_display

    @pytest.mark.parametrize(
        "admin_class,expected_filters",
        [
            (CountryAdmin, ("name",)),
            (StateAdmin, ("country",)),
            (LocalityAdmin, ("state", "state__country")),
            (AddressAdmin, ("locality", "locality__state", "locality__state__country")),
        ],
    )
    def test_admin_list_filters(self, admin_site, admin_class, expected_filters):
        """Test that each admin class has the expected list filters."""
        admin_instance = admin_class(admin_site._registry[admin_class.model].model, admin_site)
        assert admin_instance.list_filter == expected_filters
