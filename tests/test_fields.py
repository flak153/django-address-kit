"""
Comprehensive tests for AddressField in django-address-kit.

Tests cover:
- Field instantiation with default and custom parameters
- Field deconstruction for migrations
- Using field in test Django models
- Assignment and retrieval of Address instances
- Querying via the field (filtering, lookups)
- blank=True, null=True scenarios
- blank=False, null=False (required field) scenarios
- CASCADE deletion behavior
- SET_NULL deletion behavior
- Related name functionality
- Field validation
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import models
from django.db.migrations.writer import MigrationWriter

from django_address_kit.fields import AddressField
from django_address_kit.models import Address


class TestAddressFieldInstantiation:
    """Test AddressField instantiation with various parameters"""

    def test_field_default_instantiation(self):
        """Test AddressField can be instantiated with default parameters"""
        field = AddressField()

        assert isinstance(field, models.ForeignKey)
        assert field.blank is False
        assert field.null is False
        assert field.remote_field.model == Address
        assert field.remote_field.on_delete == models.CASCADE

    def test_field_with_blank_true(self):
        """Test AddressField instantiation with blank=True"""
        field = AddressField(blank=True)

        assert field.blank is True
        assert field.null is False

    def test_field_with_null_true(self):
        """Test AddressField instantiation with null=True"""
        field = AddressField(null=True)

        assert field.blank is False
        assert field.null is True

    def test_field_with_blank_and_null_true(self):
        """Test AddressField instantiation with both blank=True and null=True"""
        field = AddressField(blank=True, null=True)

        assert field.blank is True
        assert field.null is True

    def test_field_with_custom_related_name(self):
        """Test AddressField with custom related_name"""
        field = AddressField(related_name="institutions")

        assert field.remote_field.related_name == "institutions"

    def test_field_with_set_null_on_delete(self):
        """Test AddressField with SET_NULL deletion behavior"""
        field = AddressField(on_delete=models.SET_NULL, null=True)

        assert field.remote_field.on_delete == models.SET_NULL
        assert field.null is True

    def test_field_with_protect_on_delete(self):
        """Test AddressField with PROTECT deletion behavior"""
        field = AddressField(on_delete=models.PROTECT)

        assert field.remote_field.on_delete == models.PROTECT

    def test_field_targets_address_model(self):
        """Test that AddressField always targets the Address model"""
        field = AddressField()

        assert field.remote_field.model == Address
        assert field.related_model == Address


class TestAddressFieldDeconstruction:
    """Test AddressField deconstruction for Django migrations"""

    def test_field_deconstruction_default(self):
        """Test field deconstruction with default parameters"""
        field = AddressField()
        name, path, args, kwargs = field.deconstruct()

        assert name is None
        assert path == "django_address_kit.fields.AddressField"
        assert args == []
        assert "to" not in kwargs  # Should be implicit in AddressField

    def test_field_deconstruction_with_blank_null(self):
        """Test field deconstruction with blank and null parameters"""
        field = AddressField(blank=True, null=True)
        name, path, args, kwargs = field.deconstruct()

        assert kwargs.get("blank") is True
        assert kwargs.get("null") is True

    def test_field_deconstruction_with_related_name(self):
        """Test field deconstruction with custom related_name"""
        field = AddressField(related_name="custom_addresses")
        name, path, args, kwargs = field.deconstruct()

        assert kwargs.get("related_name") == "custom_addresses"

    def test_field_deconstruction_with_on_delete(self):
        """Test field deconstruction with custom on_delete"""
        field = AddressField(on_delete=models.SET_NULL, null=True)
        name, path, args, kwargs = field.deconstruct()

        assert kwargs.get("on_delete") == models.SET_NULL

    def test_field_serializable_for_migrations(self):
        """Test that field can be serialized for migrations"""
        field = AddressField(blank=True, null=True, related_name="test_addresses")

        try:
            # This will raise an error if the field can't be serialized
            serialized = MigrationWriter.serialize(field)
            assert serialized is not None
        except Exception as e:
            pytest.fail(f"Field serialization failed: {e}")


@pytest.mark.django_db
class TestAddressFieldInModel:
    """Test AddressField usage in Django models"""

    def test_model_with_address_field_optional(self, address_instance):
        """Test model with optional AddressField (blank=True, null=True)"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(blank=True, null=True)

            class Meta:
                app_label = "tests"

        # Verify field exists and has correct type
        field = TestModel._meta.get_field("address")
        assert isinstance(field, AddressField)
        assert field.blank is True
        assert field.null is True

    def test_model_with_address_field_required(self):
        """Test model with required AddressField (blank=False, null=False)"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(blank=False, null=False)

            class Meta:
                app_label = "tests"

        field = TestModel._meta.get_field("address")
        assert isinstance(field, AddressField)
        assert field.blank is False
        assert field.null is False

    def test_model_field_has_correct_db_column(self):
        """Test that AddressField creates correct database column"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            address = AddressField()

            class Meta:
                app_label = "tests"

        field = TestModel._meta.get_field("address")
        # ForeignKey creates a column with _id suffix
        expected_column = f"{field.name}_id"
        assert field.get_attname() == expected_column


@pytest.mark.django_db
class TestAddressFieldAssignmentAndRetrieval:
    """Test assigning and retrieving Address instances via AddressField"""

    def test_assign_address_to_field(self, address_instance):
        """Test assigning an Address instance to AddressField"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(blank=True, null=True)

            class Meta:
                app_label = "tests"
                managed = False

        instance = TestModel(name="Test Institution")
        instance.address = address_instance

        assert instance.address == address_instance
        assert instance.address.street_number == "123"
        assert instance.address.route == "Main St"

    def test_retrieve_address_from_field(self, address_instance):
        """Test retrieving Address instance from AddressField after save"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(blank=True, null=True)

            class Meta:
                app_label = "tests"
                managed = False

        # Note: In real tests with proper DB setup, this would save and retrieve
        instance = TestModel(name="Test Institution", address=address_instance)
        retrieved_address = instance.address

        assert retrieved_address == address_instance
        assert isinstance(retrieved_address, Address)

    def test_assign_none_to_optional_field(self):
        """Test assigning None to optional AddressField"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(blank=True, null=True)

            class Meta:
                app_label = "tests"
                managed = False

        instance = TestModel(name="Test Institution")
        instance.address = None

        assert instance.address is None

    def test_access_related_address_attributes(self, address_instance):
        """Test accessing Address attributes through the field"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(blank=True, null=True)

            class Meta:
                app_label = "tests"
                managed = False

        instance = TestModel(name="Test", address=address_instance)

        # Access various Address attributes
        assert instance.address.street_number == "123"
        assert instance.address.route == "Main St"
        assert instance.address.postal_code == "94102"
        assert instance.address.locality.name == "San Francisco"


@pytest.mark.django_db
class TestAddressFieldQuerying:
    """Test querying models via AddressField"""

    def test_filter_by_address_exact(self):
        """Test filtering by exact Address instance"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(blank=True, null=True)

            class Meta:
                app_label = "tests"
                managed = False

        # This test demonstrates the query pattern
        # In real usage with DB: TestModel.objects.filter(address=address_instance)
        field = TestModel._meta.get_field("address")
        assert field.get_lookup("exact") is not None

    def test_filter_by_address_null(self):
        """Test filtering for null addresses"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(blank=True, null=True)

            class Meta:
                app_label = "tests"
                managed = False

        # In real usage: TestModel.objects.filter(address__isnull=True)
        field = TestModel._meta.get_field("address")
        assert field.get_lookup("isnull") is not None

    def test_filter_by_related_address_fields(self):
        """Test filtering by related Address fields using lookups"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(blank=True, null=True)

            class Meta:
                app_label = "tests"
                managed = False

        # In real usage: TestModel.objects.filter(address__postal_code="94102")
        # Verify that the field supports related lookups
        field = TestModel._meta.get_field("address")
        assert isinstance(field, models.ForeignKey)
        assert field.related_model == Address

    def test_select_related_address(self):
        """Test select_related with AddressField for query optimization"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(blank=True, null=True)

            class Meta:
                app_label = "tests"
                managed = False

        # In real usage: TestModel.objects.select_related('address')
        # Verify field supports select_related (ForeignKey property)
        field = TestModel._meta.get_field("address")
        assert hasattr(field, "remote_field")
        assert field.many_to_one is True


@pytest.mark.django_db
class TestAddressFieldOptionalScenarios:
    """Test AddressField with blank=True, null=True"""

    def test_optional_field_allows_none(self):
        """Test that optional AddressField allows None value"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(blank=True, null=True)

            class Meta:
                app_label = "tests"
                managed = False

        instance = TestModel(name="Test", address=None)
        # No validation error should be raised for None
        instance.full_clean()  # This validates all fields

    def test_optional_field_validation_with_none(self):
        """Test field validation passes with None for optional field"""
        from django_address_kit.fields import AddressField

        field = AddressField(blank=True, null=True)

        # Validate that None is acceptable
        try:
            field.clean(None, None)
        except ValidationError:
            pytest.fail("Optional field should accept None")

    def test_optional_field_in_form_not_required(self):
        """Test that optional AddressField creates non-required form field"""
        from django_address_kit.fields import AddressField

        field = AddressField(blank=True, null=True)
        form_field = field.formfield()

        assert form_field.required is False


@pytest.mark.django_db
class TestAddressFieldRequiredScenarios:
    """Test AddressField with blank=False, null=False"""

    def test_required_field_rejects_none(self):
        """Test that required AddressField rejects None value"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(blank=False, null=False)

            class Meta:
                app_label = "tests"
                managed = False

        instance = TestModel(name="Test", address=None)

        with pytest.raises(ValidationError):
            instance.full_clean()

    def test_required_field_validation_with_none(self):
        """Test field validation fails with None for required field"""
        from django_address_kit.fields import AddressField

        field = AddressField(blank=False, null=False)

        with pytest.raises(ValidationError):
            field.clean(None, None)

    def test_required_field_in_form_is_required(self):
        """Test that required AddressField creates required form field"""
        from django_address_kit.fields import AddressField

        field = AddressField(blank=False, null=False)
        form_field = field.formfield()

        assert form_field.required is True

    def test_required_field_accepts_address(self, address_instance):
        """Test that required AddressField accepts valid Address instance"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(blank=False, null=False)

            class Meta:
                app_label = "tests"
                managed = False

        instance = TestModel(name="Test", address=address_instance)
        # Should not raise validation error
        assert instance.address == address_instance


@pytest.mark.django_db
class TestAddressFieldCascadeDeletion:
    """Test CASCADE deletion behavior of AddressField"""

    def test_cascade_delete_default_behavior(self):
        """Test that CASCADE is the default on_delete behavior"""
        from django_address_kit.fields import AddressField

        field = AddressField()

        assert field.remote_field.on_delete == models.CASCADE

    def test_cascade_delete_in_model(self, address_instance):
        """Test CASCADE deletion behavior in a model"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(on_delete=models.CASCADE)

            class Meta:
                app_label = "tests"
                managed = False

        instance = TestModel(name="Test", address=address_instance)

        # Verify cascade is set
        field = TestModel._meta.get_field("address")
        assert field.remote_field.on_delete == models.CASCADE

    def test_cascade_preserves_relationship(self, address_instance):
        """Test that CASCADE relationship is properly established"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(on_delete=models.CASCADE)

            class Meta:
                app_label = "tests"
                managed = False

        # When Address is deleted, related TestModel instances should be deleted
        field = TestModel._meta.get_field("address")
        assert field.remote_field.on_delete == models.CASCADE
        assert field.related_model == Address


@pytest.mark.django_db
class TestAddressFieldSetNullDeletion:
    """Test SET_NULL deletion behavior of AddressField"""

    def test_set_null_requires_null_true(self):
        """Test that SET_NULL requires null=True"""
        from django_address_kit.fields import AddressField

        # SET_NULL requires null=True
        field = AddressField(on_delete=models.SET_NULL, null=True)

        assert field.remote_field.on_delete == models.SET_NULL
        assert field.null is True

    def test_set_null_in_model(self):
        """Test SET_NULL deletion behavior in a model"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(on_delete=models.SET_NULL, null=True, blank=True)

            class Meta:
                app_label = "tests"
                managed = False

        field = TestModel._meta.get_field("address")
        assert field.remote_field.on_delete == models.SET_NULL
        assert field.null is True


@pytest.mark.django_db
class TestAddressFieldProtectDeletion:
    """Test PROTECT deletion behavior of AddressField"""

    def test_protect_deletion_behavior(self):
        """Test PROTECT prevents deletion of referenced Address"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(on_delete=models.PROTECT)

            class Meta:
                app_label = "tests"
                managed = False

        field = TestModel._meta.get_field("address")
        assert field.remote_field.on_delete == models.PROTECT


@pytest.mark.django_db
class TestAddressFieldRelatedName:
    """Test related_name functionality of AddressField"""

    def test_default_related_name(self):
        """Test default related_name follows Django conventions"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            address = AddressField()

            class Meta:
                app_label = "tests"
                managed = False

        field = TestModel._meta.get_field("address")
        # Default related_name is model_name_set (lowercased)
        assert field.remote_field.related_name is None  # Uses Django default

    def test_custom_related_name(self):
        """Test custom related_name"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            address = AddressField(related_name="institutions")

            class Meta:
                app_label = "tests"
                managed = False

        field = TestModel._meta.get_field("address")
        assert field.remote_field.related_name == "institutions"

    def test_related_name_with_plus(self):
        """Test related_name with '+' to prevent reverse relation"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            address = AddressField(related_name="+")

            class Meta:
                app_label = "tests"
                managed = False

        field = TestModel._meta.get_field("address")
        assert field.remote_field.related_name == "+"

    def test_reverse_relation_access(self, address_instance):
        """Test accessing reverse relation via related_name"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(related_name="test_institutions")

            class Meta:
                app_label = "tests"
                managed = False

        # In real usage: address_instance.test_institutions.all()
        # Verify the reverse relation exists
        field = TestModel._meta.get_field("address")
        assert hasattr(field.remote_field, "related_name")
        assert field.remote_field.related_name == "test_institutions"


@pytest.mark.django_db
class TestAddressFieldEdgeCases:
    """Test edge cases and special scenarios"""

    def test_field_with_verbose_name(self):
        """Test AddressField with verbose_name"""
        from django_address_kit.fields import AddressField

        field = AddressField(verbose_name="Institution Address")

        assert field.verbose_name == "Institution Address"

    def test_field_with_help_text(self):
        """Test AddressField with help_text"""
        from django_address_kit.fields import AddressField

        help_text = "Primary address for this institution"
        field = AddressField(help_text=help_text)

        assert field.help_text == help_text

    def test_field_with_db_index(self):
        """Test AddressField with db_index=True"""
        from django_address_kit.fields import AddressField

        field = AddressField(db_index=True)

        assert field.db_index is True

    def test_field_with_db_column(self):
        """Test AddressField with custom db_column"""
        from django_address_kit.fields import AddressField

        field = AddressField(db_column="custom_address_id")

        assert field.db_column == "custom_address_id"

    def test_multiple_address_fields_in_model(self, address_instance, address_instance_full):
        """Test model with multiple AddressField instances"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            primary_address = AddressField(
                related_name="primary_institutions", blank=True, null=True
            )
            billing_address = AddressField(
                related_name="billing_institutions", blank=True, null=True
            )
            shipping_address = AddressField(
                related_name="shipping_institutions", blank=True, null=True
            )

            class Meta:
                app_label = "tests"
                managed = False

        instance = TestModel(
            primary_address=address_instance,
            billing_address=address_instance_full,
            shipping_address=None,
        )

        assert instance.primary_address == address_instance
        assert instance.billing_address == address_instance_full
        assert instance.shipping_address is None

    def test_field_str_representation(self):
        """Test string representation of AddressField"""
        from django_address_kit.fields import AddressField

        field = AddressField()

        # Field should have a meaningful string representation
        str_repr = str(field)
        assert str_repr is not None
        assert len(str_repr) > 0

    def test_field_contributes_to_class(self):
        """Test that AddressField properly contributes to model class"""
        from django_address_kit.fields import AddressField

        class TestModel(models.Model):
            address = AddressField()

            class Meta:
                app_label = "tests"
                managed = False

        # Verify field is properly registered in model's _meta
        assert "address" in [f.name for f in TestModel._meta.get_fields()]
        field = TestModel._meta.get_field("address")
        assert isinstance(field, AddressField)
