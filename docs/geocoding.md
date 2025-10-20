# Geocoding Integration

`create_address_from_raw()` accepts injectable geocoding/parsing callables so the
library can normalize free-form address strings without hard-wiring a specific
provider. Two integration patterns are supported:

1. **Online providers** – pass a callable wrapping Google Maps, Loqate, etc. that
   returns a mapping with keys like `street_number`, `street_name`,
   `street_type`, `formatted`, `latitude`, `longitude`, and an embedded
   `location` dict containing `country`, `country_code`, `state`, `state_code`,
   `locality`, and `postal_code`.
2. **Offline parsing** – omit the geocoder and provide a parser callable to keep
   everything local (defaults to the regex-based `parse_address_components`).

The helper then reuses Country/State/Locality rows via `resolve_location`
before persisting an `Address`, ensuring the hierarchy stays normalized even
when the input payload is free-form.

Every successful geocode captures the provider payload in the
`AddressSource` model together with the normalized components snapshot and any
metadata (confidence indicators, rate-limit context, etc.). The most recent
payload per provider is available via the serializer/admin `sources`
collection for auditing or downstream analytics. The library automatically
keeps the latest three versions per provider, pruning older snapshots once new
geocode results arrive. Provider identifiers (Google `place_id`, Loqate `Id`)
are promoted to `AddressIdentifier` records so shared addresses can be matched
quickly without scanning payload blobs.

## Provider Adapters

Two ready-to-use adapters now ship with the package:

- `django_address_kit.providers.GoogleMapsAdapter`
- `django_address_kit.providers.LoqateAdapter`

Both implement the shared `GeocodeAdapter` protocol and can be plugged directly
into `create_address_from_raw`. They handle payload normalization and raise
`RateLimitError` when a provider signals quota exhaustion so the helper can back
off and retry.

```python
from django_address_kit.providers import GoogleMapsAdapter, RetryConfig
from django_address_kit.resolvers import create_address_from_raw

adapter = GoogleMapsAdapter(api_key="YOUR-API-KEY")
address = create_address_from_raw(
    "1600 Amphitheatre Pkwy, Mountain View, CA 94043",
    geocode_adapter=adapter,
    retry_config=RetryConfig(max_attempts=4, base_delay=0.25),
)
```

When you need tighter control over HTTP clients (e.g., custom session pools or
observability hooks), instantiate the adapters with pre-configured clients via
the `client` (Google) or `http_get` (Loqate) keyword arguments.

### Creating Addresses From Raw Strings

Most callers can rely on the default helper and simply pass the raw string plus
an adapter (or API key). For example, ingesting a legacy address and enriching
it with Google data:

```python
from django_address_kit.ingest import ingest_legacy_address
address = ingest_legacy_address(
    legacy_payload={
        "line1": "123 Main St",
        "city": "Boston",
        "state": "MA",
        "postal_code": "02129",
        "country": "United States",
    },
    google_api_key=settings.GOOGLE_MAPS_API_KEY,
)
```

Under the hood `create_address_from_raw` performs the geocode, persists the
normalized components, and snapshots the full provider payload in
`AddressSource`.

### Rate-Limit Handling

`create_address_from_raw` implements exponential backoff. Customize behaviour
with `RetryConfig` and, in tests, swap out the sleep function using the
`sleep_func` keyword argument to avoid slowing down your suite.

```python
address = create_address_from_raw(
    raw,
    geocode_adapter=adapter,
    retry_config=RetryConfig(max_attempts=2, base_delay=0.1, max_delay=1),
    sleep_func=lambda _: None,  # no-op sleep for deterministic tests
)
```

If all retries are exhausted the original `RateLimitError` bubbles up so callers
can decide whether to queue for later processing or surface a user-facing error.

## Secret Management

Keep API keys out of version control. Store secrets in `.env` files or your
preferred secret manager and expose them via Django settings, e.g.:

```python
# settings.py
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
```

Then pass the configured key when instantiating the adapter in your views,
serializers, or admin actions.
