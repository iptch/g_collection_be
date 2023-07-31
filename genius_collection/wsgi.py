"""
WSGI config for genius_collection project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
is_prod = 'WEBSITE_HOSTNAME' in os.environ
settings_module = 'genius_collection.production' if is_prod else 'genius_collection.settings'
# settings_module = 'genius_collection.production' if 'WEBSITE_HOSTNAME' in os.environ else 'genius_collection.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

application = get_wsgi_application()
