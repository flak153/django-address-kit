"""
Google Maps adapter providing a thin wrapper around ``googlemaps.Client``.

The adapter focuses on returning a consistent component mapping so the core
library does not need to know about provider-specific payload formats.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Sequence

from ..constants import MILITARY_STATES
from .base import ConfigurationError, GeocodeError, RateLimitError

try:  # pragma: no cover - optional dependency
    import googlemaps  # type: ignore
    from googlemaps import Client as GoogleMapsClient  # type: ignore
    from googlemaps.exceptions import ApiError  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    googlemaps = None
    GoogleMapsClient = object  # type: ignore

    class ApiError(Exception):  # type: ignore
        """Fallback ApiError placeholder when googlemaps is unavailable."""


class GoogleMapsAdapter:
    """Geocode adapter backed by the ``googlemaps`` client."""

    provider_name = "google"

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        client: Optional[GoogleMapsClient] = None,
        rate_limit_statuses: Optional[Sequence[str]] = None,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            if googlemaps is None:  # pragma: no cover - import guard
                raise ConfigurationError(
                    "googlemaps package is not installed; install the 'geocoding' extra."
                )
            if not api_key:
                raise ConfigurationError(
                    "Google Maps API key is required when no client is supplied."
                )
            self._client = googlemaps.Client(key=api_key)

        self._rate_limit_statuses = {
            status.upper() for status in rate_limit_statuses or ("OVER_QUERY_LIMIT",)
        }

    def geocode(self, query: str) -> Dict[str, Any]:
        """Resolve the query into the normalized component mapping expected by the helpers."""

        if not query or not query.strip():
            raise GeocodeError("Geocode query cannot be empty.")

        try:
            response = self._client.geocode(query)
        except ApiError as exc:  # pragma: no cover - network call guard
            status = getattr(exc, "status", "") or ""
            if status.upper() in self._rate_limit_statuses:
                raise RateLimitError(f"Google Maps rate limit exceeded: {status}") from exc
            raise GeocodeError(f"Google Maps API error: {exc}") from exc
        except Exception as exc:  # pragma: no cover - defensive
            raise GeocodeError(f"Unexpected Google Maps failure: {exc}") from exc

        if not response:
            return {}

        result = response[0]
        components = self._normalize_components(result.get("address_components", []))
        geometry = result.get("geometry") or {}
        location = geometry.get("location", {}) if isinstance(geometry, dict) else {}
        payload: Dict[str, Any] = {
            "street_number": components.get("street_number", ""),
            "street_name": components.get("street_name", components.get("route", "")),
            "route": components.get("route", ""),
            "street_type": components.get("street_type", ""),
            "street_direction": components.get("street_direction", ""),
            "unit_type": components.get("unit_type", ""),
            "unit_number": components.get("unit_number", ""),
            "formatted": result.get("formatted_address", ""),
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
            "location": {
                "country": components.get("country"),
                "country_code": components.get("country_code"),
                "state": components.get("state"),
                "state_code": components.get("state_code"),
                "locality": components.get("locality"),
                "postal_code": components.get("postal_code"),
            },
            "address_components": result.get("address_components", []),
            "geometry": geometry,
        }

        if components.get("is_po_box"):
            payload["is_po_box"] = True
        if components.get("is_military"):
            payload["is_military"] = True

        payload["provider"] = self.provider_name
        payload["raw_payload"] = {"query": query, "results": response}
        payload["metadata"] = {
            "place_id": result.get("place_id"),
            "types": result.get("types", []),
            "location_type": geometry.get("location_type"),
            "viewport": geometry.get("viewport"),
            "plus_code": result.get("plus_code"),
        }

        return payload

    def _normalize_components(self, components: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        """Translate Google component payloads into normalized keys."""

        normalized: Dict[str, Any] = {}

        for component in components:
            types = set(component.get("types", []))
            long_name = component.get("long_name") or ""
            short_name = component.get("short_name") or ""

            if "street_number" in types:
                normalized["street_number"] = long_name
            if "route" in types:
                normalized["route"] = long_name
                street_name, street_type, street_direction = self._split_route(long_name)
                normalized.setdefault("street_name", street_name)
                if street_type:
                    normalized.setdefault("street_type", street_type)
                if street_direction:
                    normalized.setdefault("street_direction", street_direction)
            if "postal_code" in types:
                normalized["postal_code"] = long_name
            if "locality" in types:
                normalized["locality"] = long_name
            if "administrative_area_level_1" in types:
                normalized["state"] = long_name
                normalized["state_code"] = short_name
                if short_name in MILITARY_STATES:
                    normalized["is_military"] = True
            if "country" in types:
                normalized["country"] = long_name
                normalized["country_code"] = short_name
            if "subpremise" in types:
                normalized["unit_type"] = (
                    component.get("types", ["Unit"])[0].replace("_", " ").title()
                )
                normalized["unit_number"] = long_name
            if "post_box" in types:
                normalized["is_po_box"] = True

        return normalized

    def _split_route(self, route: str) -> tuple[str, str, str]:
        """Naively split the route into name, type, and direction components."""

        if not route:
            return "", "", ""

        parts = route.split()
        if len(parts) == 1:
            return parts[0], "", ""

        # Attempt to detect cardinal direction prefixes.
        direction = ""
        if parts[0].upper() in {"N", "S", "E", "W", "NE", "NW", "SE", "SW"}:
            direction = parts[0].upper()
            parts = parts[1:]

        street_type = parts[-1]
        street_name = " ".join(parts[:-1]) if len(parts) > 1 else parts[0]

        return street_name.strip(), street_type, direction


__all__ = ["GoogleMapsAdapter"]
