from django.db import models

from django_address_kit.fields import AddressField
from django_address_kit.models import Address


def test_address_field_defaults_to_cascade():
    field = AddressField()

    assert isinstance(field, models.ForeignKey)
    assert field.remote_field.model is Address
    assert field.remote_field.on_delete is models.PROTECT


def test_address_field_set_null_when_nullable():
    field = AddressField(blank=True, null=True)

    assert field.null is True
    assert field.remote_field.on_delete is models.PROTECT
