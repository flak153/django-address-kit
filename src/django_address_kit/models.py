"""
Django models for US address handling.

Models:
- Country: Country information (name, code)
- State: State/province information with country relationship
- Locality: City/locality information with state relationship
- Address: Full address with optional geocoding support
"""

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

    name = models.CharField(max_length=165, blank=True)
    code = models.CharField(max_length=8, blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="states")

    class Meta:
        unique_together = ("name", "country")
        ordering = ("country", "name")

    def __str__(self) -> str:
        txt = self.to_str()
        country = str(self.country)
        if country and txt:
            txt += ", "
        txt += country
        return txt

    def to_str(self) -> str:
        """Return state name or code."""
        return f"{self.name or self.code}"


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

        if self.locality:
            parts = []
            if self.street_number:
                parts.append(self.street_number)
            if self.route:
                parts.append(self.route)
            parts.append(str(self.locality))
            return ", ".join(filter(None, parts)) if parts else self.raw

        return self.raw

    def clean(self) -> None:
        """Validate that raw field is not blank."""
        if not self.raw:
            raise ValidationError("Addresses may not have a blank `raw` field.")

    def as_dict(self) -> dict[str, Any]:
        """Return address data as a dictionary."""
        ad = {
            "street_number": self.street_number,
            "route": self.route,
            "raw": self.raw,
            "formatted": self.formatted,
            "latitude": self.latitude if self.latitude else "",
            "longitude": self.longitude if self.longitude else "",
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
