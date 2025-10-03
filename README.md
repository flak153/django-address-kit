# django-address-kit

A modern, maintained Django package for US address handling with Django REST Framework support.

## Why django-address-kit?

`django-address` is unmaintained and incompatible with modern Django versions. `django-address-kit` provides:

- ✅ Django 4.2+ and 5.x support
- ✅ Python 3.8+ compatibility
- ✅ Django REST Framework serializers included
- ✅ US address validation and formatting
- ✅ Optional geocoding support
- ✅ Migration tools from `django-address`

## Installation

```bash
pip install django-address-kit
```

Or with Poetry:

```bash
poetry add django-address-kit
```

## Quick Start

### 1. Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    ...
    'django_address_kit',
]
```

### 2. Run migrations

```bash
python manage.py migrate django_address_kit
```

### 3. Use in your models

```python
from django.db import models
from django_address_kit.fields import AddressField

class Institution(models.Model):
    name = models.CharField(max_length=100)
    address = AddressField(blank=True, null=True)
```

### 4. DRF Integration

```python
from rest_framework import serializers
from django_address_kit.serializers import AddressSerializer

class InstitutionSerializer(serializers.ModelSerializer):
    address = AddressSerializer()

    class Meta:
        model = Institution
        fields = ['name', 'address']
```

## Migrating from django-address

See [Migration Guide](docs/migration-from-django-address.md)

## License

MIT License - see [LICENSE](LICENSE)

## Maintained By

Mohammed Ali ([@flak153](https://github.com/flak153))