# django-address-kit

Modern US-address management for Django 4.2+ and Django REST Framework. Drop-in replacement for the unmaintained `django-address`, with built-in serialization, geocoding helpers, and migration tooling.

---

## Highlights

- **Django-ready**: Supports Django 4.2, 5.x and Python 3.8+ out of the box
- **Structured models**: Street typing, directions, unit metadata, PO Box & military flags
- **Reusable resolvers**: Idempotent address creation with automatic deduplication
- **Geocoder integration**: Google/Loqate adapters with retry/backoff helpers
- **Provider intel**: `AddressSource` (full payload snapshots) + `AddressIdentifier` (`place_id`, etc.)
- **Migration tooling**: Management commands to ingest legacy `django-address` data
- **Batteries included**: DRF serializers, admin inlines, faker-rich test fixtures

---

## Installation

```bash
pip install django-address-kit
```

With Poetry:

```bash
poetry add django-address-kit
```

---

## Getting Started

### 1. Install the app
```python
INSTALLED_APPS = [
    # ...
    "django_address_kit",
]
```

### 2. Run migrations
```bash
python manage.py migrate django_address_kit
```

### 3. Use the `AddressField`
```python
from django.db import models
from django_address_kit.fields import AddressField


class Customer(models.Model):
    name = models.CharField(max_length=120)
    shipping_address = AddressField(null=True)  # defaults to PROTECT on delete
```

### 4. Wire up serializers/admin
```python
from rest_framework import serializers
from django_address_kit.serializers import AddressSerializer


class CustomerSerializer(serializers.ModelSerializer):
    shipping_address = AddressSerializer(read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "name", "shipping_address"]
```

Admin inlines automatically expose captured sources and identifiers.

---

## Geocoding & Ingestion

- `create_address_from_raw` accepts a `geocode_adapter` (Google/Loqate) and stores the full payload snapshot.
- `ingest_legacy_address` + `manage.py ingest_legacy_addresses` migrate legacy data, dedupe by provider IDs, and retain every normalized snapshot.
- Use `generate_sample_legacy_addresses` and `dump_legacy_addresses` to rehearse migrations locally before pointing at production data.

Read the [Geocoding Guide](docs/geocoding.md) for adapter details and rate-limit handling.

---

## Migrating from `django-address`

See the full [Migration Guide](docs/migration-guide.md) for schema differences, resolver changes, and management command usage.

---

## Development

- Formatting & linting: `poetry run ruff format && poetry run ruff check .`
- Tests (optional live geocode):
  ```bash
  poetry run pytest
  # Set GOOGLE_MAPS_API_KEY to exercise the live ingestion test
  ```
- CI: GitHub Actions runs Ruff and the pytest suite on every push/PR (`.github/workflows/ci.yml`). Add a repository secret named `GOOGLE_MAPS_API_KEY` if you want the live geocoding test to hit Google; otherwise it will be skipped automatically.
- Faker-backed factories available at `tests/factories.py` for custom fixtures.

---

## License

MIT License – see [LICENSE](LICENSE).

---

Crafted and maintained by [Mohammed Ali](https://github.com/flak153).
