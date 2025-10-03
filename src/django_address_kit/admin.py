from django.contrib import admin
from .models import Country, State, Locality, Address


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    """Admin configuration for Country model."""

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

    list_display = ("__str__", "street_number", "route", "locality", "latitude", "longitude")
    search_fields = (
        "raw",
        "formatted",
        "street_number",
        "route",
        "locality__name",
        "locality__postal_code",
        "locality__state__name",
    )
    list_filter = ("locality", "locality__state", "locality__state__country")
    readonly_fields = ("formatted",)

    def get_readonly_fields(self, request, obj=None):
        """Make specific fields read-only based on user permissions."""
        if not request.user.is_superuser:
            return self.readonly_fields + ("latitude", "longitude")
        return self.readonly_fields

# Add AddressInline to LocalityAdmin
LocalityAdmin.inlines = [AddressInline]
