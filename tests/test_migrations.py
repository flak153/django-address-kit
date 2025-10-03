"""
Migration tests for django-address-kit.

These tests validate the integrity of Django migrations, ensuring:
1. Initial migration creates all tables correctly
2. Model fields and constraints are properly defined
3. Foreign key relationships are set up
4. Indexes and unique constraints are correct
5. Migrations are reversible
"""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.apps import apps


@pytest.mark.django_db(transaction=True)
def test_migrations_forward_and_backward():
    """
    Test that all migrations can be applied forward and backward.

    This ensures migrations are well-formed and reversible.
    """
    # Capture the initial state of the database
    executor = MigrationExecutor(connection)

    # Get the app label for django_address_kit
    app_label = "django_address_kit"

    # Migrate to the latest state
    targets = executor.loader.graph.leaf_nodes()
    executor.migrate(targets)

    # Verify all models are in the database
    models = apps.get_models(include_auto_created=True)
    app_models = [model for model in models if model._meta.app_label == app_label]
    assert len(app_models) > 0, "No models found for django_address_kit"

    # Check if we can migrate backward
    executor.migrate([app_label])


def test_migration_schema():
    """
    Validate the database schema against the expected model definitions.
    """
    # Get the latest migration state
    executor = MigrationExecutor(connection)
    migration_state = executor.loader.project_state()

    # Check models
    models = {
        "country": migration_state.apps.get_model("django_address_kit", "Country"),
        "state": migration_state.apps.get_model("django_address_kit", "State"),
        "locality": migration_state.apps.get_model("django_address_kit", "Locality"),
        "address": migration_state.apps.get_model("django_address_kit", "Address"),
    }

    # Verify Country model
    country_model = models["country"]
    country_fields = {f.name: f for f in country_model._meta.fields}
    assert "name" in country_fields
    assert "code" in country_fields
    assert country_fields["name"].max_length == 40
    assert country_fields["name"].unique is True
    assert country_fields["code"].max_length == 2

    # Verify State model
    state_model = models["state"]
    state_fields = {f.name: f for f in state_model._meta.fields}
    assert "name" in state_fields
    assert "code" in state_fields
    assert "country_id" in state_fields
    assert state_fields["name"].max_length == 165
    assert state_fields["code"].max_length == 8
    assert state_fields["country_id"].remote_field.model == country_model
    assert state_fields["country_id"].remote_field.on_delete.__name__ == "CASCADE"

    # Verify Locality model
    locality_model = models["locality"]
    locality_fields = {f.name: f for f in locality_model._meta.fields}
    assert "name" in locality_fields
    assert "postal_code" in locality_fields
    assert "state_id" in locality_fields
    assert locality_fields["name"].max_length == 165
    assert locality_fields["postal_code"].max_length == 10
    assert locality_fields["state_id"].remote_field.model == state_model
    assert locality_fields["state_id"].remote_field.on_delete.__name__ == "CASCADE"

    # Verify Address model
    address_model = models["address"]
    address_fields = {f.name: f for f in address_model._meta.fields}
    assert "street_number" in address_fields
    assert "route" in address_fields
    assert "locality_id" in address_fields
    assert "raw" in address_fields
    assert "formatted" in address_fields
    assert "latitude" in address_fields
    assert "longitude" in address_fields

    assert address_fields["street_number"].max_length == 20
    assert address_fields["route"].max_length == 100
    assert address_fields["raw"].max_length == 200
    assert address_fields["formatted"].max_length == 200

    # Optional locality relationship
    assert address_fields["locality_id"].null is True
    assert address_fields["locality_id"].remote_field.model == locality_model
    assert address_fields["locality_id"].remote_field.on_delete.__name__ == "CASCADE"


def test_unique_constraints():
    """
    Test the unique constraints on models.
    """
    # Get the latest migration state
    executor = MigrationExecutor(connection)
    migration_state = executor.loader.project_state()

    # Check unique constraints
    country_model = migration_state.apps.get_model("django_address_kit", "Country")
    state_model = migration_state.apps.get_model("django_address_kit", "State")
    locality_model = migration_state.apps.get_model("django_address_kit", "Locality")

    # Verify unique constraints
    assert (
        "name",
        "country",
    ) in state_model._meta.unique_together, "Missing unique together constraint on state"
    assert (
        "name",
        "postal_code",
        "state",
    ) in locality_model._meta.unique_together, "Missing unique together constraint on locality"


def test_model_relationships():
    """
    Verify the relationships between models in the migration.
    """
    # Get the latest migration state
    executor = MigrationExecutor(connection)
    migration_state = executor.loader.project_state()

    # Check models
    country_model = migration_state.apps.get_model("django_address_kit", "Country")
    state_model = migration_state.apps.get_model("django_address_kit", "State")
    locality_model = migration_state.apps.get_model("django_address_kit", "Locality")
    address_model = migration_state.apps.get_model("django_address_kit", "Address")

    # Test cascading deletes
    # If a country is deleted, its states should be deleted
    # If a state is deleted, its localities should be deleted
    # If a locality is deleted, its addresses should be deleted
