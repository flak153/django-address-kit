import re


def normalize_string(s: str) -> str:
    """
    Normalize a string by stripping whitespace and standardizing formatting.

    Args:
        s (str): Input string to normalize

    Returns:
        str: Normalized string
    """
    if not s:
        return s

    # Remove extra whitespaces, leading/trailing whitespaces
    normalized = re.sub(r"\s+", " ", s).strip()

    # Optionally title case the string, preserving first letter case in some cases
    return normalized.title() if normalized.isupper() else normalized


def parse_address_components(address: str) -> dict:
    """
    Parse a full address string into its components.

    Args:
        address (str): Full address string

    Returns:
        dict: Parsed address components
    """
    # Preliminary parsing regex patterns
    patterns = [
        # PO Box pattern
        r"(?:PO\s*Box\s*(?P<po_box>\d+))?",
        # Unit/Apartment pattern
        r"(?:(?P<unit>(?:Apt|Unit|#)\s*\w+))?",
        # Street address pattern
        r"(?:(?P<street_number>\d+)\s*"
        + r"(?P<street_name>[\w\s]+)"
        + r"(?P<street_type>Street|St|Rd|Road|Ave|Avenue|Blvd|Boulevard|Pkwy|Parkway))?",
        # City, State, Zip pattern
        r"(?:(?P<city>[\w\s]+),\s*" + r"(?P<state>[A-Z]{2})\s*" + r"(?P<zipcode>\d{5}(?:-\d{4})?))",
    ]

    full_pattern = r"\s*".join(patterns)
    match = re.search(full_pattern, address, re.IGNORECASE)

    if not match:
        return {}

    # Convert to a dict, removing None values
    return {k: v for k, v in match.groupdict().items() if v is not None}


def standardize_address(address: str) -> str:
    """
    Standardize an address by normalizing its format.

    Args:
        address (str): Address to standardize

    Returns:
        str: Standardized address
    """
    if not address:
        return address

    # Normalize spacing and casing
    address = normalize_string(address)

    # Expand common abbreviations
    # Note: You might want to use a more comprehensive library for this
    abbreviations = {"Pkwy": "Parkway", "St": "Street", "CA": "California"}

    for abbr, full in abbreviations.items():
        address = address.replace(abbr, full)

    return address
