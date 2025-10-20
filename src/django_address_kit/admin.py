from django.contrib import admin, messages

from .models import Address, AddressIdentifier, AddressSource, Country, Locality, State
from .resolvers import create_address_from_raw


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    """Admin configuration for Country model."""

    model = Country
    list_display = ("name", "code")
    search_fields = ("name", "code")
    list_filter = ("name",)
    inlines = []  # Will be set after StateInline is defined


class StateInline(admin.TabularInline):
    """Inline admin for States within a Country."""

    model = State
    extra = 1
    show_change_link = True


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    """Admin configuration for State model."""

    model = State
    list_display = ("name", "code", "country")
    search_fields = ("name", "code", "country__name")
    list_filter = ("country",)
    inlines = []  # Will be set after LocalityInline is defined


# Add StateInline to CountryAdmin
CountryAdmin.inlines = [StateInline]


class LocalityInline(admin.TabularInline):
    """Inline admin for Localities within a State."""

    model = Locality
    extra = 1
    show_change_link = True


@admin.register(Locality)
class LocalityAdmin(admin.ModelAdmin):
    """Admin configuration for Locality model."""

    model = Locality
    list_display = ("name", "postal_code", "state")
    search_fields = ("name", "postal_code", "state__name", "state__country__name")
    list_filter = ("state", "state__country")
    inlines = []  # Will be set after AddressInline is defined


# Add LocalityInline to StateAdmin
StateAdmin.inlines = [LocalityInline]


class AddressInline(admin.TabularInline):
    """Inline admin for Addresses within a Locality."""

    model = Address
    extra = 1
    show_change_link = True


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Admin configuration for Address model."""

    model = Address
    list_display = (
        "__str__",
        "street_number",
        "street_name",
        "street_type",
        "unit_number",
        "locality",
        "latitude",
        "longitude",
        "is_po_box",
    )
    search_fields = (
        "raw",
        "formatted",
        "street_number",
        "street_name",
        "route",
        "locality__name",
        "locality__postal_code",
        "locality__state__name",
    )
    list_filter = ("locality", "locality__state", "locality__state__country")
    readonly_fields = ("formatted",)
    actions = ["normalize_from_raw"]
    inlines = []  # populated after AddressSourceInline definition

    def get_readonly_fields(self, request, obj=None):
        """Make specific fields read-only based on user permissions."""
        if not request.user.is_superuser:
            return self.readonly_fields + ("latitude", "longitude")
        return self.readonly_fields

    @admin.action(description="Normalize selected addresses from raw string")
    def normalize_from_raw(self, request, queryset):
        """Recompute structured fields using the resolver helpers."""
        updated = 0
        for address in queryset:
            normalized = create_address_from_raw(address.raw)
            for field in [
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
            ]:
                setattr(address, field, getattr(normalized, field))
            address.locality = normalized.locality
            address.save()
            updated += 1

        messages.success(
            request,
            f"Normalized {updated} address{'es' if updated != 1 else ''} from raw strings.",
        )


# Add AddressInline to LocalityAdmin
LocalityAdmin.inlines = [AddressInline]


class AddressSourceInline(admin.StackedInline):
    """Read-only inline displaying captured provider payloads."""

    model = AddressSource
    extra = 0
    can_delete = False
    readonly_fields = (
        "provider",
        "version",
        "created_at",
        "raw_payload",
        "normalized_components",
        "metadata",
    )
    show_change_link = False


# Attach inline to Address admin after its declaration
AddressAdmin.inlines = [AddressSourceInline]


class AddressIdentifierInline(admin.TabularInline):
    model = AddressIdentifier
    extra = 0
    can_delete = False
    readonly_fields = ("provider", "identifier", "created_at")
    show_change_link = False


AddressAdmin.inlines.append(AddressIdentifierInline)
