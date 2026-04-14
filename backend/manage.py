#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# Load the correct .env file BEFORE Django reads any settings.
# Set APP_ENV=production (or staging) in the shell to switch environments.
from config.config_loader import load_env
load_env()


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
