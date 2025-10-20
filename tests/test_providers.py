import pytest

from django_address_kit.providers.google import GoogleMapsAdapter
from django_address_kit.providers.loqate import LoqateAdapter


class DummyGoogleClient:
    def geocode(self, query: str):
        return [
            {
                "formatted_address": "1600 Amphitheatre Parkway, Mountain View, CA 94043, USA",
                "geometry": {
                    "location": {"lat": 37.4224764, "lng": -122.0842499},
                    "location_type": "ROOFTOP",
                    "viewport": {
                        "northeast": {"lat": 37.42382538029149, "lng": -122.0829009197085},
                        "southwest": {"lat": 37.4211274197085, "lng": -122.0855988802915},
                    },
                },
                "place_id": "ChIJ2eUgeAK6j4ARbn5u_wAGqWA",
                "types": ["street_address"],
                "address_components": [
                    {"long_name": "1600", "short_name": "1600", "types": ["street_number"]},
                    {
                        "long_name": "Amphitheatre Parkway",
                        "short_name": "Amphitheatre Pkwy",
                        "types": ["route"],
                    },
                    {
                        "long_name": "Mountain View",
                        "short_name": "Mountain View",
                        "types": ["locality", "political"],
                    },
                    {
                        "long_name": "Santa Clara County",
                        "short_name": "Santa Clara County",
                        "types": ["administrative_area_level_2", "political"],
                    },
                    {
                        "long_name": "California",
                        "short_name": "CA",
                        "types": ["administrative_area_level_1", "political"],
                    },
                    {
                        "long_name": "United States",
                        "short_name": "US",
                        "types": ["country", "political"],
                    },
                    {"long_name": "94043", "short_name": "94043", "types": ["postal_code"]},
                ],
                "plus_code": {"compound_code": "CWC8+W5 Mountain View, California"},
            }
        ]


@pytest.mark.parametrize("query", ["1600 Amphitheatre Parkway, Mountain View, CA 94043"])
def test_google_adapter_maps_payload(query):
    adapter = GoogleMapsAdapter(client=DummyGoogleClient())
    result = adapter.geocode(query)

    assert result["provider"] == "google"
    assert result["street_number"] == "1600"
    assert result["street_name"] == "Amphitheatre"
    assert result["route"] == "Amphitheatre Parkway"
    assert result["latitude"] == 37.4224764
    assert result["metadata"]["place_id"] == "ChIJ2eUgeAK6j4ARbn5u_wAGqWA"
    assert "viewport" in result["metadata"]
    assert result["geometry"]["location"]["lat"] == 37.4224764
    assert result["raw_payload"]["results"][0]["place_id"] == "ChIJ2eUgeAK6j4ARbn5u_wAGqWA"


def test_loqate_adapter_parses_verify_payload():
    response = [
        {
            "Input": {"Address": "123 Main St Boston MA 02129", "Country": "US"},
            "Matches": [
                {
                    "AQI": "A",
                    "AVC": "V44-I44-P7-100",
                    "Address": "123 Main St,Boston MA 02129-3533",
                    "AdministrativeArea": "MA",
                    "Country": "US",
                    "CountryName": "United States",
                    "DeliveryAddress": "123 Main St",
                    "DeliveryAddress1": "123 Main St",
                    "Locality": "Boston",
                    "MatchRuleLabel": "Rlhng",
                    "PostalCode": "02129-3533",
                    "PostalCodePrimary": "02129",
                    "PostalCodeSecondary": "3533",
                    "Premise": "123",
                    "PremiseNumber": "123",
                    "Sequence": "1",
                    "SubAdministrativeArea": "Suffolk",
                    "Thoroughfare": "Main St",
                }
            ],
        }
    ]

    adapter = LoqateAdapter(api_key="dummy", http_get=lambda endpoint, params: response)
    result = adapter.geocode("123 Main St Boston MA 02129")

    assert result["provider"] == "loqate"
    assert result["street_number"] == "123"
    assert result["route"] == "Main St"
    assert result["location"]["locality"] == "Boston"
    assert result["metadata"]["aqi"] == "A"
    assert result["raw_payload"]["Matches"][0]["PostalCodePrimary"] == "02129"
