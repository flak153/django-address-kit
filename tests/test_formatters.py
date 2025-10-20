import pytest
from django_address_kit.formatters import (
    format_us_address,
    format_multiline_address,
    format_short_address,
    get_address_display_string,
)


@pytest.mark.parametrize(
    "components, expected_format",
    [
        (
            {
                "street_number": "123",
                "street_name": "Main",
                "street_type": "Street",
                "city": "Anytown",
                "state": "NY",
                "zipcode": "12345",
            },
            "123 Main Street, Anytown, NY 12345",
        ),
        (
            {
                "street_number": "456",
                "street_name": "Oak",
                "street_type": "Avenue",
                "unit_type": "Apt",
                "unit_number": "2B",
                "city": "Somewhere",
                "state": "CA",
                "zipcode": "54321",
            },
            "456 Oak Avenue, Apt 2B, Somewhere, CA 54321",
        ),
    ],
)
def test_format_us_address(components, expected_format):
    """Test US address formatting."""
    assert format_us_address(components) == expected_format


def test_format_multiline_address():
    """Test multiline address formatting."""
    address_components = {
        "street_number": "789",
        "street_name": "Maple",
        "street_type": "Road",
        "city": "Elsewhere",
        "state": "TX",
        "zipcode": "67890",
    }

    expected_multiline = ["789 Maple Road", "Elsewhere, TX 67890"]

    assert format_multiline_address(address_components) == expected_multiline


def test_format_short_address():
    """Test short address formatting."""
    address_components = {"street_name": "Broadway", "city": "New York", "state": "NY"}

    expected_short = "Broadway, New York, NY"
    assert format_short_address(address_components) == expected_short


def test_get_address_display_string():
    """Test comprehensive address display string generation."""
    full_components = {
        "street_number": "100",
        "street_name": "Tech",
        "street_type": "Circle",
        "unit_type": "Suite",
        "unit_number": "500",
        "city": "Silicon Valley",
        "state": "CA",
        "zipcode": "94000",
    }

    default_display = get_address_display_string(full_components)
    assert default_display == "100 Tech Circle, Suite 500, Silicon Valley, CA 94000"

    # Test with specific display options
    compact_display = get_address_display_string(full_components, style="compact")
    assert compact_display == "100 Tech Cir., Suite 500, Silicon Valley, CA 94000"

    short_display = get_address_display_string(full_components, style="short")
    assert short_display == "Tech Circle, Silicon Valley, CA"
