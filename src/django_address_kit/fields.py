"""
Custom Django model fields for address handling.

Provides AddressField for easy integration into Django models.
"""

from django.db import models

from .models import Address


class AddressField(models.ForeignKey):
    """
    A custom field for addresses in Django models.

    Usage:
        class Institution(models.Model):
            name = models.CharField(max_length=100)
            address = AddressField(blank=True, null=True)

    This field is a ForeignKey to the Address model with special handling
    to make it easier to use addresses in models.
    """

    description = "An address field"

    def __init__(self, *args, **kwargs):
        kwargs["to"] = "django_address_kit.Address"
        default_on_delete = models.SET_NULL if kwargs.get("null", False) else models.CASCADE
        kwargs["on_delete"] = kwargs.get("on_delete", default_on_delete)
        super().__init__(*args, **kwargs)
