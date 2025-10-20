# Migration Guide

This project intentionally diverges from the legacy `django-address` schema in a few places to
improve data integrity and modernize integrations. Use the checklist below when upgrading.

## Model Changes

- **State** records now require both `name` and `code`. Codes are uppercased automatically and
  must be unique per country (`unique_state_code_per_country`). Audit any fixture data that relied
  on blank codes.
- **Address** gains richer structure:
  - `street_name`, `street_type`, and `street_direction` replace the legacy `route` string.
    The old `route` column remains for backwards compatibility and is kept in sync automatically.
  - `unit_type` and `unit_number` capture apartment/suite metadata instead of baking it into
    the free-form street line.
  - Boolean flags `is_po_box` and `is_military` allow downstream consumers to branch on special
    handling without reparsing strings.
- **AddressSource** is a new table that tracks the raw geocoder payload, the normalized
  component snapshot used to populate the address, and any provider-specific metadata.
  Each address/provider pair stores the latest payload so you can audit or replay enrichments.
- **AddressIdentifier** stores stable provider identifiers (e.g., Google `place_id`, Loqate `Id`).
  When new geocodes arrive the latest identifier is stamped automatically, enabling fast
  deduplication of shared addresses across owners.
- Use `ingest_legacy_address()` to migrate historic django-address rows. Provide the legacy
  field mapping and an optional Google API key; the helper will call
  `create_address_from_components` when structured data is present or fall back to
  `create_address_from_raw` with the Google adapter when enrichment is required.

Run `poetry run python manage.py makemigrations` followed by `migrate` to create the new columns.
For existing databases, backfill `street_name` from `route` and populate missing state codes before
deploying the migration.

## Resolver & Serializer Updates

- `create_address_from_raw` accepts `geocode_adapter` instances and now exposes a `RetryConfig`
  for rate-limit aware retries.
- `AddressSerializer` delegates to the resolver helpers so API consumers automatically benefit
  from normalized location hierarchy and component syncing.
- Admin actions include a "Normalize from raw" tool that re-runs the resolver pipeline against
  stored `raw` strings.

## Test Fixture Guidance

- Provide `country` objects whenever creating states in tests; the new constraints enforce it.
- Prefer Faker-generated factories from `tests/factories.py` to avoid brittle hard-coded addresses.
- When asserting query behaviour, use `django_assert_num_queries` to lock in expected ORM access
  patterns.
- For interactive dry runs: `python manage.py generate_sample_legacy_addresses --count 100`
  followed by `python manage.py dump_legacy_addresses --output legacy.jsonl`. Add your
  `GOOGLE_MAPS_API_KEY` to a local `.env`, then run
  `python manage.py ingest_legacy_addresses --input legacy.jsonl --geocode-missing --google-api-key $GOOGLE_MAPS_API_KEY`.
  The management command reports the number of deduplicated addresses created.

Refer to `TODO.md` for any remaining follow ups and open issues related to additional provider
support.
