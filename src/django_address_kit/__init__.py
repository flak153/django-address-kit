"""
django-address-kit: A modern Django package for US address handling
"""

__version__ = "0.1.0"

default_app_config = "django_address_kit.apps.DjangoAddressKitConfig"

# Avoid circular imports by using lazy imports
__all__ = [
    "AddressField",
    "Address",
    "Country",
    "Locality",
    "State",
]


def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name == "AddressField":
        from .fields import AddressField

        return AddressField
    elif name == "Address":
        from .models import Address

        return Address
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
