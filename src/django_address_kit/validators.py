"""US address validators for django-address-kit"""

import re
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from .constants import ALL_STATE_CODES


def validate_state_code(value: str) -> None:
    """
    Validate that the state code is a valid 2-character US state, territory, or military code.

    Args:
        value: The state code to validate (e.g., 'CA', 'NY', 'PR', 'AA')

    Raises:
        ValidationError: If the state code is not valid

    Examples:
        >>> validate_state_code('CA')  # Valid - California
        >>> validate_state_code('PR')  # Valid - Puerto Rico
        >>> validate_state_code('AA')  # Valid - Armed Forces Americas
        >>> validate_state_code('ZZ')  # Raises ValidationError
    """
    if not value:
        raise ValidationError("State code is required.")

    # Convert to uppercase for case-insensitive validation
    state_code = value.strip().upper()

    if len(state_code) != 2:
        raise ValidationError(
            f"State code must be exactly 2 characters. Got: {len(state_code)} characters."
        )

    if state_code not in ALL_STATE_CODES:
        raise ValidationError(
            f'"{value}" is not a valid US state, territory, or military postal code.'
        )


def validate_zip_code(value: str) -> None:
    """
    Validate that the ZIP code is in valid 5-digit or ZIP+4 format.

    Args:
        value: The ZIP code to validate (e.g., '12345' or '12345-6789')

    Raises:
        ValidationError: If the ZIP code format is invalid

    Examples:
        >>> validate_zip_code('12345')       # Valid - 5 digit
        >>> validate_zip_code('12345-6789')  # Valid - ZIP+4
        >>> validate_zip_code('1234')        # Raises ValidationError
    """
    if not value:
        raise ValidationError("ZIP code is required.")

    zip_code = value.strip()

    # Pattern for 5-digit ZIP or ZIP+4 format
    zip_pattern = r"^\d{5}(-\d{4})?$"

    if not re.match(zip_pattern, zip_code):
        raise ValidationError(
            f'"{value}" is not a valid ZIP code. Use 5-digit (12345) or ZIP+4 (12345-6789) format.'
        )


def validate_street_address(value: str) -> None:
    """
    Validate basic US street address format.

    A valid street address should:
    - Start with a number (street number)
    - Contain alphanumeric characters and common punctuation
    - Not be just numbers or just special characters
    - Have reasonable length (at least 5 characters)

    Args:
        value: The street address to validate

    Raises:
        ValidationError: If the street address format is invalid

    Examples:
        >>> validate_street_address('123 Main St')           # Valid
        >>> validate_street_address('456 Oak Avenue Apt 2B')  # Valid
        >>> validate_street_address('789 E. Pine Blvd.')      # Valid
        >>> validate_street_address('Main St')                # Raises ValidationError (no number)
    """
    if not value:
        raise ValidationError("Street address is required.")

    address = value.strip()

    if len(address) < 5:
        raise ValidationError("Street address must be at least 5 characters long.")

    # Must start with a number (street number)
    if not re.match(r"^\d", address):
        raise ValidationError("Street address must start with a street number.")

    # Must contain at least one letter (street name)
    if not re.search(r"[a-zA-Z]", address):
        raise ValidationError("Street address must contain a street name.")

    # Check for valid characters (alphanumeric, spaces, and common punctuation)
    if not re.match(r"^[\w\s\.\-\#\,\/]+$", address):
        raise ValidationError(
            "Street address contains invalid characters. Use only letters, numbers, spaces, and common punctuation (., -, #, ,, /)."
        )


def validate_po_box(value: str) -> None:
    """
    Validate PO Box format.

    Accepts various PO Box formats:
    - PO Box 123
    - P.O. Box 123
    - POB 123
    - P O Box 123

    Args:
        value: The PO Box to validate

    Raises:
        ValidationError: If the PO Box format is invalid

    Examples:
        >>> validate_po_box('PO Box 123')     # Valid
        >>> validate_po_box('P.O. Box 456')   # Valid
        >>> validate_po_box('POB 789')        # Valid
        >>> validate_po_box('Box 123')        # Raises ValidationError (missing PO/P.O.)
    """
    if not value:
        raise ValidationError("PO Box is required.")

    po_box = value.strip()

    # Pattern for various PO Box formats
    # Matches: PO Box, P.O. Box, P O Box, POB, P.O.B, etc.
    po_box_pattern = r"^(P\.?\s*O\.?\s*(Box|B\.?)|POB\.?)\s+\d+$"

    if not re.match(po_box_pattern, po_box, re.IGNORECASE):
        raise ValidationError(
            f'"{value}" is not a valid PO Box format. Use formats like "PO Box 123", "P.O. Box 123", or "POB 123".'
        )


# Django RegexValidator instances for use in model fields
state_code_validator = RegexValidator(
    regex=r"^[A-Z]{2}$",
    message="State code must be a valid 2-letter US state, territory, or military postal code.",
)

zip_code_validator = RegexValidator(
    regex=r"^\d{5}(-\d{4})?$",
    message="ZIP code must be in 5-digit (12345) or ZIP+4 (12345-6789) format.",
)
