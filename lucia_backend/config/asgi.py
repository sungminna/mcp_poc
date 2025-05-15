"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

# Set Django settings module before importing any Django components
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Import Django ASGI application first
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

# Import other components after Django is configured
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from channels.auth import AuthMiddlewareStack # Django's standard auth middleware
# from chat_manager.middleware import JWTAuthMiddlewareStack # Old middleware
from .middleware import TokenAuthMiddlewareStack # New middleware from config/middleware.py
import chat_manager.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": TokenAuthMiddlewareStack(
        URLRouter(
            chat_manager.routing.websocket_urlpatterns
        )
    )
})
