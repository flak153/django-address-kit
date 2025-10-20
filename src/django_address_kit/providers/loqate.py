"""
Loqate geocoding adapter with a pluggable HTTP client hook.

The adapter intentionally keeps the HTTP layer abstract so projects can plug in
their preferred requests/session tooling while still benefiting from retry and
rate-limit handling supplied by ``create_address_from_raw``.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .base import ConfigurationError, GeocodeError, RateLimitError

DEFAULT_ENDPOINT = "https://api.addressy.com/Capture/Interactive/Find/v1.10/json3.ws"


class LoqateAdapter:
    """Simple wrapper around Loqate's REST API."""

    provider_name = "loqate"

    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str = DEFAULT_ENDPOINT,
        http_get: Optional[Callable[[str, dict[str, Any]], Any]] = None,
    ) -> None:
        if not api_key:
            raise ConfigurationError("Loqate API key is required.")

        self._api_key = api_key
        self._endpoint = endpoint
        self._http_get = http_get

    def geocode(self, query: str) -> Dict[str, Any]:
        """Resolve the query using Loqate's Interactive Find service."""

        if not query or not query.strip():
            raise GeocodeError("Geocode query cannot be empty.")

        response = self._perform_request(
            {
                "Key": self._api_key,
                "Text": query,
                "IsMiddleware": False,
                "Countries": "USA",
            }
        )

        if not response:
            return {}

        payload = response[0] if isinstance(response, list) else response

        # Handle Verify/Geocode style responses where matches are returned.
        matches = payload.get("Matches", [])
        if matches:
            match = matches[0]
            normalized = self._normalize_match(match)
            normalized["provider"] = self.provider_name
            normalized["raw_payload"] = payload
            normalized["metadata"] = {
                "aqi": match.get("AQI"),
                "avc": match.get("AVC"),
                "match_rule": match.get("MatchRuleLabel"),
                "sequence": match.get("Sequence"),
                "input": payload.get("Input"),
            }
            return normalized

        items = payload.get("Items", [])
        if not items:
            return {}

        first = items[0]
        if first.get("Error"):
            if str(first.get("Error")).upper() in {"1006", "1023", "429"}:
                raise RateLimitError(first.get("Description", "Loqate rate limit exceeded"))
            raise GeocodeError(first.get("Description", "Loqate error"))

        normalized = self._normalize_item(first)
        normalized["provider"] = self.provider_name
        normalized["raw_payload"] = first
        normalized["metadata"] = {"input": payload.get("Input")}
        return normalized

    def _perform_request(self, params: dict[str, Any]) -> dict[str, Any]:
        """Dispatch the HTTP request using the configured client."""

        if self._http_get:
            return self._http_get(self._endpoint, params)

        try:  # pragma: no cover - optional dependency
            import requests
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ConfigurationError(
                "requests is required when no custom http_get callable is supplied."
            ) from exc

        response = requests.get(self._endpoint, params=params, timeout=5)  # type: ignore[arg-type]
        if response.status_code == 429:
            raise RateLimitError("Loqate rate limit exceeded (HTTP 429)")
        response.raise_for_status()
        return response.json()

    def _normalize_item(self, item: dict[str, Any]) -> Dict[str, Any]:
        """Convert a Loqate response item to the normalized component mapping."""

        # Loqate requires a subsequent Retrieve call for full components, but the
        # interactive lookup already contains enough data for our purposes.
        payload = {
            "street_number": item.get("BuildingNumber", ""),
            "street_name": item.get("Street", ""),
            "street_type": item.get("StreetType", ""),
            "unit_type": item.get("SecondaryStreetType", ""),
            "unit_number": item.get("SecondaryStreetNumber", ""),
            "formatted": item.get("Text", ""),
            "latitude": item.get("Latitude"),
            "longitude": item.get("Longitude"),
            "location": {
                "locality": item.get("City", ""),
                "state": item.get("ProvinceName", item.get("Province", "")),
                "state_code": item.get("Province", ""),
                "postal_code": item.get("PostalCode", ""),
                "country": item.get("CountryName", ""),
                "country_code": item.get("CountryIso2", ""),
            },
        }

        payload["provider"] = self.provider_name
        payload["raw_payload"] = item
        payload["metadata"] = {
            "id": item.get("Id"),
            "type": item.get("Type"),
        }

        return payload

    def _normalize_match(self, match: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a Verify/Matches payload."""

        street_number = match.get("PremiseNumber") or match.get("Premise", "")
        thoroughfare = match.get("Thoroughfare", "")
        formatted = match.get("Address") or match.get("DeliveryAddress") or ""

        return {
            "street_number": street_number,
            "street_name": thoroughfare,
            "route": thoroughfare,
            "street_type": "",
            "unit_type": "",
            "unit_number": match.get("SubPremise", ""),
            "formatted": formatted,
            "latitude": match.get("Latitude"),
            "longitude": match.get("Longitude"),
            "location": {
                "locality": match.get("Locality", ""),
                "state": match.get("AdministrativeArea", ""),
                "state_code": match.get("AdministrativeArea", ""),
                "postal_code": match.get("PostalCode", ""),
                "country": match.get("CountryName", ""),
                "country_code": match.get("Country", ""),
            },
        }


__all__ = ["LoqateAdapter"]
