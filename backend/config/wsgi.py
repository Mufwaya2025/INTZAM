"""WSGI config for IntZam LMS project."""
import os
from config.config_loader import load_env

# Load correct .env before Django initialises.
load_env()

from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()
