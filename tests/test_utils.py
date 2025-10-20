from django_address_kit.utils import normalize_string, parse_address_components, standardize_address


def test_normalize_string_trims_and_collapses_whitespace():
    assert normalize_string("  123   MAIN st ") == "123 MAIN st"


def test_parse_address_components_breaks_into_fields():
    components = parse_address_components("1600 Amphitheatre Pkwy, Mountain View, CA 94043")

    assert components["street_number"] == "1600"
    assert components["street_name"] == "Amphitheatre"
    assert components["street_type"] == "PKWY"
    assert components["city"] == "Mountain View"
    assert components["state"] == "CA"
    assert components["zipcode"] == "94043"


def test_parse_address_components_handles_po_box_and_units():
    components = parse_address_components(
        "PO Box 123, Apt 4B, 742 Evergreen Terrace, Springfield, IL 62704"
    )

    assert components["po_box"] == "123"
    assert components["unit_type"] == "APT"
    assert components["unit_number"] == "4B"
    assert components["street_number"] == "742"
    assert components["street_name"].startswith("Evergreen")


def test_standardize_address_expands_suffixes():
    result = standardize_address("1600 Amphitheatre Pkwy, Mountain View, CA 94043")
    assert "Parkway" in result
