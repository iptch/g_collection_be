#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

from dotenv import load_dotenv


def main():
    """Run administrative tasks."""
    # os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'genius_collection.settings')
    is_prod = 'WEBSITE_HOSTNAME' in os.environ
    if not is_prod:
        print("Loading environment variables from .env file")
        load_dotenv('./.env')

    settings_module = "genius_collection.production" if is_prod else 'genius_collection.settings'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
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
