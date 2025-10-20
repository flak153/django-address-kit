"""
Django models for US address handling.

Models:
- Country: Country information (name, code)
- State: State/province information with country relationship
- Locality: City/locality information with state relationship
- Address: Full address with optional geocoding support
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models


class Country(models.Model):
    """Represents a country with name and ISO code."""

    name = models.CharField(max_length=40, unique=True, blank=True)
    code = models.CharField(max_length=2, blank=True)

    class Meta:
        verbose_name_plural = "Countries"
        ordering = ("name",)

    def __str__(self) -> str:
        return f"{self.name or self.code}"


class State(models.Model):
    """Represents a state/province with country relationship."""

    name = models.CharField(max_length=165)
    code = models.CharField(max_length=8)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="states")

    class Meta:
        unique_together = ("name", "country")
        constraints = [
            models.UniqueConstraint(
                fields=("code", "country"),
                name="unique_state_code_per_country",
            )
        ]
        ordering = ("country", "name")

    def __str__(self) -> str:
        parts = [self.to_str()]
        country = str(self.country)
        if country:
            parts.append(country)
        return ", ".join(filter(None, parts))

    def to_str(self) -> str:
        """Return state name or code."""
        return f"{self.code or self.name}"

    def clean(self) -> None:
        """Normalize and validate state data."""
        self.code = (self.code or "").strip().upper()
        self.name = (self.name or "").strip()

        if not self.code:
            raise ValidationError({"code": "State code cannot be blank."})
        if not self.name:
            raise ValidationError({"name": "State name cannot be blank."})

    def save(self, *args, **kwargs):
        """Persist the state after normalization and validation."""
        self.full_clean()
        return super().save(*args, **kwargs)


class Locality(models.Model):
    """Represents a city/locality with state relationship."""

    name = models.CharField(max_length=165, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name="localities")

    class Meta:
        verbose_name_plural = "Localities"
        unique_together = ("name", "postal_code", "state")
        ordering = ("state", "name")

    def __str__(self) -> str:
        txt = f"{self.name}"
        state = self.state.to_str() if self.state else ""
        if txt and state:
            txt += ", "
        txt += state
        if self.postal_code:
            txt += f" {self.postal_code}"
        cntry = str(self.state.country) if self.state and self.state.country else ""
        if cntry:
            txt += f", {cntry}"
        return txt


class Address(models.Model):
    """
    Represents a complete address with optional geocoding.

    Fields:
    - street_number: Building/house number
    - route: Street name
    - locality: Foreign key to Locality
    - raw: Unformatted address string (required)
    - formatted: Formatted address string
    - latitude: Geocoded latitude (optional)
    - longitude: Geocoded longitude (optional)
    """

    street_number = models.CharField(max_length=20, blank=True)
    route = models.CharField(max_length=100, blank=True)
    street_name = models.CharField(max_length=100, blank=True)
    street_type = models.CharField(max_length=20, blank=True)
    street_direction = models.CharField(max_length=2, blank=True)
    unit_type = models.CharField(max_length=20, blank=True)
    unit_number = models.CharField(max_length=20, blank=True)
    is_po_box = models.BooleanField(default=False)
    is_military = models.BooleanField(default=False)
    locality = models.ForeignKey(
        Locality,
        on_delete=models.CASCADE,
        related_name="addresses",
        blank=True,
        null=True,
    )
    raw = models.CharField(max_length=200)
    formatted = models.CharField(max_length=200, blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Addresses"
        ordering = ("locality", "route", "street_number")

    def __str__(self) -> str:
        if self.formatted:
            return self.formatted

        primary = " ".join(
            filter(
                None,
                [
                    self.street_number,
                    self.street_direction,
                    self.street_name or self.route,
                    self.street_type,
                ],
            )
        )
        unit = " ".join(filter(None, [self.unit_type, self.unit_number]))
        locality_display = str(self.locality) if self.locality else ""

        parts = [primary, unit, locality_display]
        label = ", ".join(filter(None, [part.strip() for part in parts if part]))
        return label or self.raw

    def clean(self) -> None:
        """Validate that raw field is not blank."""
        if not self.raw:
            raise ValidationError("Addresses may not have a blank `raw` field.")

    def as_dict(self) -> dict[str, Any]:
        """Return address data as a dictionary."""
        ad: dict[str, Any] = {
            "street_number": self.street_number,
            "street_name": self.street_name or self.route,
            "route": self.route,
            "street_type": self.street_type,
            "street_direction": self.street_direction,
            "unit_type": self.unit_type,
            "unit_number": self.unit_number,
            "raw": self.raw,
            "formatted": self.formatted,
            "latitude": self.latitude if self.latitude is not None else "",
            "longitude": self.longitude if self.longitude is not None else "",
            "is_po_box": self.is_po_box,
            "is_military": self.is_military,
        }

        if self.locality:
            ad["locality"] = self.locality.name
            ad["postal_code"] = self.locality.postal_code
            if self.locality.state:
                ad["state"] = self.locality.state.name
                ad["state_code"] = self.locality.state.code
                if self.locality.state.country:
                    ad["country"] = self.locality.state.country.name
                    ad["country_code"] = self.locality.state.country.code

        return ad

    @property
    def postal_code(self) -> str:
        """Expose locality postal code directly on Address for convenience."""
        return self.locality.postal_code if self.locality else ""

    @postal_code.setter
    def postal_code(self, value: str) -> None:
        """Persist postal code assignments onto the related locality."""
        if not self.locality:
            raise AttributeError("Cannot set postal_code when address has no locality")
        self.locality.postal_code = value

    def save(self, *args, **kwargs):
        """Normalize component fields before saving."""
        self._synchronize_street_fields()
        self.raw = (self.raw or "").strip()
        self.formatted = (self.formatted or "").strip()
        self._auto_detect_po_box()
        self.full_clean()
        return super().save(*args, **kwargs)

    def _synchronize_street_fields(self) -> None:
        """Keep legacy `route` field in sync with `street_name`."""
        street = (self.street_name or "").strip()
        route = (self.route or "").strip()

        self.street_number = (self.street_number or "").strip()

        if street and not route:
            self.route = street
        elif route and not street:
            self.street_name = route
        else:
            self.street_name = street
            self.route = route

        self.street_type = (self.street_type or "").strip()
        self.street_direction = (self.street_direction or "").strip().upper()
        self.unit_type = (self.unit_type or "").strip()
        self.unit_number = (self.unit_number or "").strip()

    def _auto_detect_po_box(self) -> None:
        """Automatically flag PO Box addresses when not set explicitly."""
        if self.is_po_box:
            return

        hints = " ".join(
            filter(
                None,
                [
                    self.street_number,
                    self.street_name,
                    self.raw,
                ],
            )
        )
        normalized = hints.lower()
        self.is_po_box = "po box" in normalized or "post office box" in normalized


class AddressSource(models.Model):
    """Captured provider payloads used to build an Address."""

    address = models.ForeignKey(Address, on_delete=models.CASCADE, related_name="sources")
    provider = models.CharField(max_length=40)
    version = models.PositiveSmallIntegerField(default=1)
    raw_payload = models.JSONField(default=dict)
    normalized_components = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("address", "provider", "version")
        ordering = ("-created_at", "-version")

    def __str__(self) -> str:
        return f"{self.provider} source for address {self.address_id}"


class AddressIdentifier(models.Model):
    """Provider-specific identifiers (place IDs, etc.) attached to an address."""

    address = models.ForeignKey(Address, on_delete=models.CASCADE, related_name="identifiers")
    provider = models.CharField(max_length=40)
    identifier = models.CharField(max_length=160)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("provider", "identifier")
        ordering = ("provider", "identifier")

    def __str__(self) -> str:
        return f"{self.provider}:{self.identifier}"
