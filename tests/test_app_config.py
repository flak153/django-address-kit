"""
Tests for django-address-kit application configuration.

This module checks:
1. App configuration
2. Model registration
3. Default settings
"""

import pytest
from django.apps import apps
from django.conf import settings


def test_app_configuration():
    """
    Verify that the django-address-kit app is properly configured.
    """
    # Check app is in INSTALLED_APPS
    assert "django_address_kit" in settings.INSTALLED_APPS, "App not added to INSTALLED_APPS"

    # Verify app config
    app_config = apps.get_app_config("django_address_kit")
    assert app_config is not None, "App config not found"
    assert app_config.name == "django_address_kit", "Incorrect app name in config"


def test_model_registration():
    """
    Ensure all models are registered correctly.
    """
    # Expected models
    expected_models = {"country", "state", "locality", "address"}

    # Get registered models for this app
    app_models = apps.get_app_config("django_address_kit").models
    registered_models = {name.lower() for name in app_models.keys()}

    # Check all expected models are registered
    assert expected_models.issubset(
        registered_models
    ), f"Missing models. Expected: {expected_models}, Found: {registered_models}"


def test_model_strings():
    """
    Verify __str__ methods for models.
    """
    # Import models dynamically to ensure they're loaded
    from django_address_kit.models import Country, State, Locality, Address

    # Test Country __str__
    country = Country(name="United States", code="US")
    assert str(country) == "United States", "Country __str__ method incorrect"
    country_no_name = Country(code="US")
    assert str(country_no_name) == "US", "Country __str__ method incorrect for name-less country"

    # Test State __str__
    state = State(name="California", code="CA", country=country)
    assert "California, United States" in str(state), "State __str__ method incorrect"
    state_no_name = State(code="CA", country=country)
    assert "CA, United States" in str(
        state_no_name
    ), "State __str__ method incorrect for name-less state"

    # Test Locality __str__
    locality = Locality(name="San Francisco", postal_code="94105", state=state)
    assert "San Francisco" in str(locality), "Locality __str__ method incorrect"

    # Test Address __str__
    address = Address(
        street_number="123",
        route="Main St",
        raw="123 Main St, San Francisco, CA 94105",
        locality=locality,
    )
    assert "123 Main St" in str(address), "Address __str__ method incorrect"


def test_address_validation():
    """
    Verify custom validation for Address model.
    """
    from django.core.exceptions import ValidationError
    from django_address_kit.models import Address

    # Test raw field validation
    with pytest.raises(ValidationError, match="Addresses may not have a blank `raw` field."):
        address = Address(raw="")
        address.clean()

    # Test valid address creation
    address = Address(raw="123 Test St, Testville, TS 12345")
    address.clean()  # Should not raise an exception
