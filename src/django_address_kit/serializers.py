"""
Django REST Framework serializers for address models.

Provides full CRUD serializers for:
- Country
- State (with nested Country)
- Locality (with nested State)
- Address (with nested Locality)

Supports both simple string input and structured object input for addresses.
"""

from rest_framework import serializers

from .models import Address, Country, Locality, State


class CountrySerializer(serializers.ModelSerializer):
    """Serializer for country information."""

    class Meta:
        model = Country
        fields = ["name", "code"]

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

    class Meta:
        model = Address
        fields = [
            "id",
            "street_number",
            "route",
            "locality",
            "raw",
            "formatted",
            "latitude",
            "longitude",
        ]
        read_only_fields = ["id"]

    def validate_raw(self, value: str) -> str:
        """Validate that raw address is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Raw address cannot be empty")
        return value

    def create(self, validated_data: dict) -> Address:
        """Create address with optional locality relationship."""
        locality_data = validated_data.pop("locality", None)
        locality = None

        if locality_data:
            locality_serializer = LocalitySerializer(data=locality_data)
            if locality_serializer.is_valid(raise_exception=True):
                locality = locality_serializer.save()

        return Address.objects.create(**validated_data, locality=locality)

    def update(self, instance: Address, validated_data: dict) -> Address:
        """Update address instance with optional locality update."""
        locality_data = validated_data.pop("locality", None)

        if locality_data:
            if instance.locality:
                locality_serializer = LocalitySerializer(instance.locality, data=locality_data)
            else:
                locality_serializer = LocalitySerializer(data=locality_data)

            if locality_serializer.is_valid(raise_exception=True):
                instance.locality = locality_serializer.save()

        instance.street_number = validated_data.get("street_number", instance.street_number)
        instance.route = validated_data.get("route", instance.route)
        instance.raw = validated_data.get("raw", instance.raw)
        instance.formatted = validated_data.get("formatted", instance.formatted)
        instance.latitude = validated_data.get("latitude", instance.latitude)
        instance.longitude = validated_data.get("longitude", instance.longitude)
        instance.save()
        return instance
