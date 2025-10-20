"""
Django REST Framework serializers for address models.

Provides full CRUD serializers for:
- Country
- State (with nested Country)
- Locality (with nested State)
- Address (with nested Locality)

Supports both simple string input and structured object input for addresses.
"""

from typing import Optional

from rest_framework import serializers

from .models import Address, AddressIdentifier, AddressSource, Country, Locality, State
from .resolvers import (
    LocationPayload,
    create_address_from_components,
    create_address_from_raw,
    resolve_location,
)


class CountrySerializer(serializers.ModelSerializer):
    """Serializer for country information."""

    class Meta:
        model = Country
        fields = ["name", "code"]
        extra_kwargs = {
            "name": {"validators": []},
        }

    def validate(self, attrs: dict) -> dict:
        """Validate country data."""
        if attrs.get("code") and len(attrs["code"]) != 2:
            raise serializers.ValidationError("Country code must be 2 characters")
        return attrs

    def create(self, validated_data: dict) -> Country:
        """Create or get existing country to prevent duplicates."""
        country, _ = Country.objects.get_or_create(
            name=validated_data.get("name"), defaults={"code": validated_data.get("code", "")}
        )
        return country

    def update(self, instance: Country, validated_data: dict) -> Country:
        """Update country instance."""
        instance.name = validated_data.get("name", instance.name)
        instance.code = validated_data.get("code", instance.code)
        instance.save()
        return instance


class StateSerializer(serializers.ModelSerializer):
    """Serializer for state/province information with nested country."""

    country = CountrySerializer(required=False)

    class Meta:
        model = State
        fields = ["name", "code", "country"]
        validators = []
        extra_kwargs = {
            "name": {"validators": []},
            "code": {"validators": []},
        }

    def validate(self, attrs: dict) -> dict:
        """Validate state data."""
        if attrs.get("code") and len(attrs["code"]) > 8:
            raise serializers.ValidationError("State code must be 8 characters or less")
        return attrs

    def create(self, validated_data: dict) -> State:
        """Create state with optional country relationship."""
        country_data = validated_data.pop("country", None)
        country = None

        if country_data:
            country_serializer = CountrySerializer()
            country = country_serializer.create(country_data)

        state, _ = State.objects.get_or_create(
            name=validated_data.get("name"),
            country=country,
            defaults={"code": validated_data.get("code", "")},
        )
        return state

    def update(self, instance: State, validated_data: dict) -> State:
        """Update state instance with optional country update."""
        country_data = validated_data.pop("country", None)

        if country_data:
            country_serializer = CountrySerializer()
            country = country_serializer.create(country_data)
            instance.country = country

        instance.name = validated_data.get("name", instance.name)
        instance.code = validated_data.get("code", instance.code)
        instance.save()
        return instance


class LocalitySerializer(serializers.ModelSerializer):
    """Serializer for city/locality information with nested state."""

    state = StateSerializer(required=False)

    class Meta:
        model = Locality
        fields = ["name", "postal_code", "state"]
        validators = []

    def validate_postal_code(self, value: str) -> str:
        """Validate postal code format."""
        if value and not any(c.isdigit() for c in value):
            raise serializers.ValidationError("Postal code must contain at least one number")
        return value

    def create(self, validated_data: dict) -> Locality:
        """Create locality with optional state relationship."""
        state_data = validated_data.pop("state", None)
        state = None

        if state_data:
            state_serializer = StateSerializer()
            state = state_serializer.create(state_data)

        locality, _ = Locality.objects.get_or_create(
            name=validated_data.get("name"),
            postal_code=validated_data.get("postal_code", ""),
            state=state,
            defaults={},
        )
        return locality

    def update(self, instance: Locality, validated_data: dict) -> Locality:
        """Update locality instance with optional state update."""
        state_data = validated_data.pop("state", None)

        if state_data:
            if instance.state:
                state_serializer = StateSerializer(instance.state, data=state_data)
                if state_serializer.is_valid(raise_exception=True):
                    instance.state = state_serializer.save()
            else:
                state_serializer = StateSerializer()
                instance.state = state_serializer.create(state_data)

        instance.name = validated_data.get("name", instance.name)
        instance.postal_code = validated_data.get("postal_code", instance.postal_code)
        instance.save()
        return instance


class AddressSerializer(serializers.ModelSerializer):
    """
    Serializer for US address handling.

    Required Fields:
    - raw: Unformatted input address string

    Optional Fields:
    - street_number: Building number
    - route: Street name
    - locality: Nested object with city, state, zip info
    - formatted: Formatted address string
    - latitude: Geocoded latitude
    - longitude: Geocoded longitude

    Supports both simple string input and structured object input:
    - Simple: {"raw": "123 Main St, Springfield, IL 62701"}
    - Structured: {"raw": "...", "street_number": "123", "locality": {...}}
    """

    locality = LocalitySerializer(required=False, allow_null=True)
    sources = serializers.SerializerMethodField(read_only=True)
    identifiers = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Address
        fields = [
            "id",
            "street_number",
            "street_name",
            "street_type",
            "street_direction",
            "unit_type",
            "unit_number",
            "route",
            "locality",
            "raw",
            "formatted",
            "latitude",
            "longitude",
            "is_po_box",
            "is_military",
            "sources",
            "identifiers",
        ]
        read_only_fields = ["id", "sources", "identifiers"]

    def validate_raw(self, value: str) -> str:
        """Validate that raw address is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Raw address cannot be empty")
        return value

    def create(self, validated_data: dict) -> Address:
        """Create address using resolver helpers for normalization."""
        locality_payload = _extract_location_payload(validated_data.pop("locality", None))
        components = _extract_address_components(validated_data)
        raw_value = validated_data["raw"]

        if components or locality_payload:
            return create_address_from_components(
                address_data=components,
                location_data=locality_payload,
                raw=raw_value,
            )

        return create_address_from_raw(
            raw_value,
            geocode_adapter=self.context.get("geocode_adapter"),
            geocode_func=self.context.get("geocode_func"),
            parser=self.context.get("parser"),
        )

    def update(self, instance: Address, validated_data: dict) -> Address:
        """Update address instance, reusing resolver helpers for locality."""
        locality_payload = _extract_location_payload(validated_data.pop("locality", None))

        if locality_payload is not None:
            locality = resolve_location(LocationPayload.from_mapping(locality_payload))
            instance.locality = locality

        components = _extract_address_components(validated_data)
        for field, value in components.items():
            setattr(instance, field, value)

        if "raw" in validated_data:
            instance.raw = validated_data["raw"]

        instance.save()
        return instance

    def get_sources(self, instance: Address) -> list[dict]:
        sources = instance.sources.order_by("-version")
        serializer = AddressSourceSerializer(sources, many=True, context=self.context)
        return serializer.data

    def get_identifiers(self, instance: Address) -> list[dict]:
        identifiers = instance.identifiers.order_by("provider", "identifier")
        serializer = AddressIdentifierSerializer(identifiers, many=True)
        return serializer.data


class AddressSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddressSource
        fields = [
            "provider",
            "version",
            "raw_payload",
            "normalized_components",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class AddressIdentifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddressIdentifier
        fields = ["provider", "identifier", "created_at"]
        read_only_fields = fields


def _extract_address_components(data: dict) -> dict:
    """Extract address component fields from validated serializer data."""

    component_fields = {
        "street_number",
        "street_name",
        "street_type",
        "street_direction",
        "unit_type",
        "unit_number",
        "route",
        "formatted",
        "latitude",
        "longitude",
        "is_po_box",
        "is_military",
    }

    components = {field: data[field] for field in component_fields if field in data}

    return components


def _extract_location_payload(locality_data: Optional[dict]) -> Optional[dict]:
    """Convert nested locality serializer data into resolver-friendly mapping."""

    if not locality_data:
        return None

    state_data = locality_data.get("state") or {}
    country_data = state_data.get("country") or {}

    return {
        "locality": locality_data.get("name", ""),
        "postal_code": locality_data.get("postal_code", ""),
        "state": state_data.get("name", ""),
        "state_code": state_data.get("code", ""),
        "country": country_data.get("name", ""),
        "country_code": country_data.get("code", ""),
    }
