"""
django-address-kit: A modern Django package for US address handling
"""

__version__ = "0.1.0"

default_app_config = "django_address_kit.apps.DjangoAddressKitConfig"

# Avoid circular imports by using lazy imports
__all__ = [
    "AddressField",
    "Address",
    "AddressSource",
    "AddressIdentifier",
    "Country",
    "Locality",
    "State",
    "ingest_legacy_address",
]


def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name == "AddressField":
        from .fields import AddressField

        return AddressField
    elif name == "Address":
        from .models import Address

        return Address
    elif name == "AddressSource":
        from .models import AddressSource

        return AddressSource
    elif name == "AddressIdentifier":
        from .models import AddressIdentifier

        return AddressIdentifier
    elif name == "ingest_legacy_address":
        from .ingest import ingest_legacy_address

        return ingest_legacy_address
    elif name == "Country":
        from .models import Country

        return Country
    elif name == "Locality":
        from .models import Locality

        return Locality
    elif name == "State":
        from .models import State

        return State
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
