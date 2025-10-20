"""Utility helpers for parsing and normalizing address strings."""

from __future__ import annotations

import re
from typing import Dict

from .constants import STREET_SUFFIXES, UNIT_TYPES

PO_BOX_RE = re.compile(
    r"\b(?:P\.?\s*O\.?\s*Box|Post\s+Office\s+Box)\s*(?P<po_box>[\w-]+)", re.IGNORECASE
)
UNIT_RE = re.compile(
    r"\b(?P<unit_type>Apt|Apartment|Suite|Ste|Unit|Floor|Fl|Room|Rm|Bldg|Building|#)\s*"
    r"[#\s]*(?P<unit_number>[\w-]+)",
    re.IGNORECASE,
)
CITY_STATE_RE = re.compile(
    r"(?P<city>[^,]+),\s*(?P<state>[A-Z]{2})\s*(?P<zipcode>\d{5}(?:-\d{4})?)?$"
)
CARDINAL_DIRECTIONS = {"N", "S", "E", "W", "NE", "NW", "SE", "SW"}
STREET_SUFFIX_LOOKUP = {
    **{key.upper(): key.title() for key in STREET_SUFFIXES},
    **{abbr.upper(): abbr for abbr in STREET_SUFFIXES.values()},
}


def normalize_string(value: str) -> str:
    """
    Normalize a string by stripping whitespace and standardizing formatting.

    Args:
        value (str): Input string to normalize

    Returns:
        str: Normalized string
    """
    if not value:
        return value

    normalized = re.sub(r"\s+", " ", value).strip()
    return normalized.title() if normalized.isupper() else normalized


def parse_address_components(address: str) -> Dict[str, str]:
    """
    Parse a full address string into its components.

    Args:
        address (str): Full address string

    Returns:
        dict: Parsed address components
    """
    if not address:
        return {}

    working = address.strip()
    components: Dict[str, str] = {}

    # Detect PO Box addresses.
    po_box_match = PO_BOX_RE.search(working)
    if po_box_match:
        components["po_box"] = po_box_match.group("po_box")
        working = PO_BOX_RE.sub("", working).strip(", ")

    # Extract city/state/zip from the trailing segment.
    city_state_match = CITY_STATE_RE.search(working)
    if city_state_match:
        components["city"] = city_state_match.group("city").strip()
        components["state"] = city_state_match.group("state").strip()
        zipcode = city_state_match.group("zipcode")
        if zipcode:
            components["zipcode"] = zipcode.strip()
        working = working[: city_state_match.start()].strip(", ")

    # Extract unit details if present.
    unit_match = UNIT_RE.search(working)
    if unit_match:
        unit_type = unit_match.group("unit_type") or ""
        unit_number = unit_match.group("unit_number") or ""
        components["unit_type"] = _normalize_unit_type(unit_type)
        components["unit_number"] = unit_number.strip()
        working = UNIT_RE.sub("", working).strip(", ")

    tokens = [token for token in re.split(r"\s+", working) if token]

    if tokens and tokens[0].isdigit():
        components["street_number"] = tokens.pop(0)

    if tokens and tokens[0].rstrip(",.").upper() in CARDINAL_DIRECTIONS:
        components["street_direction"] = tokens.pop(0).rstrip(",.").upper()

    if tokens:
        last_token = tokens[-1].rstrip(",.")
        last_upper = last_token.upper()
        if last_upper in STREET_SUFFIX_LOOKUP:
            components["street_type"] = STREET_SUFFIX_LOOKUP[last_upper]
            tokens.pop()

        components["street_name"] = " ".join(tokens).strip(", ")

    return {key: value for key, value in components.items() if value}


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

    address = normalize_string(address)

    for long_name, abbr in STREET_SUFFIXES.items():
        pattern = re.compile(rf"\b{abbr}\b", re.IGNORECASE)
        address = pattern.sub(long_name.title(), address)

    return address


def _normalize_unit_type(raw_type: str) -> str:
    """Normalize unit labels to USPS-style abbreviations."""

    cleaned = raw_type.replace(".", "").replace("#", "").upper()

    for name, abbr in UNIT_TYPES.items():
        if cleaned == name or cleaned == abbr:
            return abbr

    return cleaned or raw_type


__all__ = ["normalize_string", "parse_address_components", "standardize_address"]
