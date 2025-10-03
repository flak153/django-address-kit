"""Root conftest for pytest configuration"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set Django settings module before Django apps load
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

import django

django.setup()
