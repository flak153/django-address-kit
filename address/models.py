from __future__ import annotations

from django.db import models


class Address(models.Model):
    """Minimal legacy django-address stand-in for tests."""

    raw = models.CharField(max_length=255, blank=True)
    address1 = models.CharField(max_length=255, blank=True)
    address2 = models.CharField(max_length=255, blank=True)
    locality = models.CharField(max_length=128, blank=True)
    state = models.CharField(max_length=64, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=128, blank=True)

    class Meta:
        verbose_name = "Legacy Address"
        verbose_name_plural = "Legacy Addresses"

    def __str__(self) -> str:
        return self.raw or self.address1 or ""
