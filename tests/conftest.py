"""Pytest configuration and fixtures for django-address-kit tests"""

import pytest
from django.apps import apps
from django.db import models

pytest_plugins = ["pytest_django"]


@pytest.fixture
def country_instance(db):
    """Create and return a Country instance for testing"""
    from django_address_kit.models import Country

    country, _ = Country.objects.get_or_create(
        code="US", defaults={"name": "United States"}
    )
    return country


@pytest.fixture
def state_instance(db, country_instance):
    """Create and return a State instance for testing"""
    from django_address_kit.models import State

    state, _ = State.objects.get_or_create(
        code="CA",
        defaults={"name": "California", "country": country_instance},
    )
    return state


@pytest.fixture
def locality_instance(db, state_instance):
    """Create and return a Locality instance for testing"""
    from django_address_kit.models import Locality

    locality, _ = Locality.objects.get_or_create(
        name="San Francisco", state=state_instance, defaults={"postal_code": "94102"}
    )
    return locality


@pytest.fixture
def address_instance(db, locality_instance):
    """Create and return an Address instance for testing"""
    from django_address_kit.models import Address

    address = Address.objects.create(
        street_number="123",
        route="Main St",
        locality=locality_instance,
        raw="123 Main St, San Francisco, CA 94102",
        formatted="123 Main St\nSan Francisco, CA 94102",
    )
    return address


@pytest.fixture
def address_instance_full(db, locality_instance):
    """Create and return a fully populated Address instance"""
    from django_address_kit.models import Address

    address = Address.objects.create(
        street_number="456",
        route="Market St",
        raw="456 Market St, Apt 101, San Francisco, CA 94103",
        locality=locality_instance,
        formatted="456 Market St, Apt 101\nSan Francisco, CA 94103",
        latitude=37.7749,
        longitude=-122.4194,
    )
    return address


@pytest.fixture
def test_model_class(db):
    """Create a test Django model that uses AddressField"""
    from django_address_kit.fields import AddressField

    class TestModelWithAddress(models.Model):
        name = models.CharField(max_length=100)
        address = AddressField(
            blank=True, null=True, related_name="test_models", on_delete=models.CASCADE
        )

        class Meta:
            app_label = "tests"

    return TestModelWithAddress


@pytest.fixture
def test_model_required_class(db):
    """Create a test Django model with required AddressField"""
    from django_address_kit.fields import AddressField

    class TestModelRequiredAddress(models.Model):
        name = models.CharField(max_length=100)
        address = AddressField(
            blank=False, null=False, related_name="required_test_models", on_delete=models.CASCADE
        )

        class Meta:
            app_label = "tests"

    return TestModelRequiredAddress


@pytest.fixture
def test_model_set_null_class(db):
    """Create a test Django model with SET_NULL deletion behavior"""
    from django_address_kit.fields import AddressField

    class TestModelSetNull(models.Model):
        name = models.CharField(max_length=100)
        address = AddressField(
            blank=True, null=True, related_name="set_null_test_models", on_delete=models.SET_NULL
        )

        class Meta:
            app_label = "tests"

    return TestModelSetNull


# Commented out as pytest-django handles migrations automatically
# @pytest.fixture(autouse=True)
# def setup_test_models(db):
#     """
#     Register test models dynamically for each test.
#     This ensures models are available during test execution.
#     """
#     from django.core.management import call_command
#
#     # Create tables for all registered models
#     call_command("migrate", "--run-syncdb", verbosity=0)
