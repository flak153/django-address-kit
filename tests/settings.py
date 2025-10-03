"""
Django test settings for django-address-kit.
"""

SECRET_KEY = "test-secret-key-for-testing-only"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "rest_framework",
    "django_address_kit.apps.DjangoAddressKitConfig",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "ATOMIC_REQUESTS": False,
        "OPTIONS": {
            "timeout": 20,
        },
    }
}

# Minimum required Django settings for test environment
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
