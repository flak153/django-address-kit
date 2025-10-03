import pytest
from django_address_kit.utils import normalize_string, parse_address_components, standardize_address


@pytest.mark.parametrize(
    "input_string, expected",
    [
        ("  John Doe  ", "John Doe"),
        ("  123 MAIN St.  ", "123 Main St"),
        ("123   Main   Street", "123 Main Street"),
    ],
)
def test_normalize_string(input_string, expected):
    """Test string normalization utility."""
    assert normalize_string(input_string) == expected


def test_parse_address_components():
    """Test parsing full address into components."""
    address = "1600 Amphitheatre Parkway, Mountain View, CA 94043"
    components = parse_address_components(address)

    assert components["street_number"] == "1600"
    assert components["street_name"] == "Amphitheatre"
    assert components["street_type"] == "Parkway"
    assert components["city"] == "Mountain View"
    assert components["state"] == "CA"
    assert components["zipcode"] == "94043"


def test_parse_address_components_edge_cases():
    """Test parsing address with variations and edge cases."""
    # PO Box
    pobox_address = "PO Box 123, Springfield, IL 62701"
    pobox_components = parse_address_components(pobox_address)
    assert pobox_components["po_box"] == "123"
    assert pobox_components["city"] == "Springfield"
    assert pobox_components["state"] == "IL"

    # Apartment/Unit
    unit_address = "Apt 4B, 123 Main St, New York, NY 10001"
    unit_components = parse_address_components(unit_address)
    assert unit_components["street_number"] == "123"
    assert unit_components["unit"] == "Apt 4B"
    assert unit_components["city"] == "New York"


def test_standardize_address():
    """Test address standardization."""
    variations = [
        "1600 Amphitheatre Pkwy, Mountain View, CA 94043",
        "1600 Amphitheatre Parkway, Mountain View, California 94043",
        "1600 Amphitheatre Pkwy, MountainView, CA, 94043",
    ]

    standardized = standardize_address(variations[0])
    for variant in variations[1:]:
        assert standardize_address(variant) == standardized


def test_standardize_address_edge_cases():
    """Test address standardization with challenging inputs."""
    assert standardize_address("") == ""
    assert standardize_address("Incomplete Address") == "Incomplete Address"
