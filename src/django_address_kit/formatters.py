def format_us_address(components: dict, separator: str = ", ") -> str:
    """
    Format a US address from address components.

    Args:
        components (dict): Dictionary of address components
        separator (str, optional): Separator between address parts. Defaults to ', '.

    Returns:
        str: Formatted address string
    """
    parts = []

    # Main street address
    street_address = " ".join(
        filter(
            None,
            [
                components.get("street_number", ""),
                components.get("street_direction", ""),
                components.get("street_name", ""),
                components.get("street_type", ""),
            ],
        )
    )
    parts.append(street_address)

    # Optional unit/apartment
    unit_fragment = _unit_fragment(components)
    if unit_fragment:
        parts.append(unit_fragment)

    # City, state, zipcode
    location = _compose_location_line(components)

    if location:
        parts.append(location)

    return separator.join(parts)


def format_multiline_address(components: dict) -> list:
    """
    Format address into two lines.

    Args:
        components (dict): Address components

    Returns:
        list: Two-line address representation
    """
    first_line = " ".join(
        filter(
            None,
            [
                components.get("street_number", ""),
                components.get("street_direction", ""),
                components.get("street_name", ""),
                components.get("street_type", ""),
            ],
        )
    )

    second_line = _compose_location_line(components)

    return [first_line, second_line]


def format_short_address(components: dict) -> str:
    """
    Create a short, location-focused address representation.

    Args:
        components (dict): Address components

    Returns:
        str: Short address string
    """
    primary = " ".join(
        filter(
            None,
            [components.get("street_name", ""), components.get("street_type", "")],
        )
    )
    parts = [
        primary,
        components.get("city", ""),
        components.get("state", ""),
    ]
    return ", ".join(filter(None, parts))


def get_address_display_string(components: dict, style: str = "default") -> str:
    """
    Generate a flexible address display string with different styles.

    Args:
        components (dict): Address components
        style (str, optional): Display style. Defaults to 'default'.
            Options: 'default', 'compact', 'short'

    Returns:
        str: Formatted address display string
    """
    if style == "compact":
        # Abbreviate street type
        street_type_abbr = {
            "Street": "St.",
            "Avenue": "Ave.",
            "Road": "Rd.",
            "Circle": "Cir.",
            "Parkway": "Pkwy.",
        }

        # Modify components for compact style
        compact_components = components.copy()
        street_type = components.get("street_type", "")
        compact_components["street_type"] = street_type_abbr.get(street_type, street_type)

        return format_us_address(compact_components)

    elif style == "short":
        return format_short_address(components)

    else:
        return format_us_address(components)


def _unit_fragment(components: dict) -> str:
    """Return a human-readable unit fragment from component data."""

    if components.get("unit"):
        return components["unit"]

    unit_type = components.get("unit_type", "")
    unit_number = components.get("unit_number", "")

    fragment = " ".join(filter(None, [unit_type, unit_number]))
    return fragment


def _compose_location_line(components: dict) -> str:
    """Format the city/state/ZIP fragment."""

    city = components.get("city", "")
    state = components.get("state", "")
    zipcode = components.get("zipcode", "")
    state_zip = " ".join(filter(None, [state, zipcode]))

    if city and state_zip:
        return f"{city}, {state_zip}"

    return ", ".join(filter(None, [city, state_zip]))
