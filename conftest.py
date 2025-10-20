"""Root conftest for pytest configuration"""

import os
import sys
from pathlib import Path

import django
from dotenv import load_dotenv

# Load environment variables from .env if present.
load_dotenv()

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set Django settings module before Django apps load
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

django.setup()
