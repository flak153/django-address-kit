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
                components.get("street_name", ""),
                components.get("street_type", ""),
            ],
        )
    )
    parts.append(street_address)

    # Optional unit/apartment
    if components.get("unit"):
        parts.append(components["unit"])

    # City, state, zipcode
    location = " ".join(
        filter(
            None,
            [
                components.get("city", ""),
                components.get("state", ""),
                components.get("zipcode", ""),
            ],
        )
    )

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
                components.get("street_name", ""),
                components.get("street_type", ""),
            ],
        )
    )

    second_line = ", ".join(
        filter(
            None,
            [
                components.get("city", ""),
                " ".join(
                    filter(None, [components.get("state", ""), components.get("zipcode", "")])
                ),
            ],
        )
    )

    return [first_line, second_line]


def format_short_address(components: dict) -> str:
    """
    Create a short, location-focused address representation.

    Args:
        components (dict): Address components

    Returns:
        str: Short address string
    """
    parts = [
        components.get("street_name", ""),
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
