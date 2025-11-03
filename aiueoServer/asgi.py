"""
ASGI config for aiueoServer project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

# ---------------------------------python-socketio------------------------------------
# import os
# import django
# from django.core.asgi import get_asgi_application
# from socketio import ASGIApp
# from chat.socketio_events import sio
#
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
# django.setup()
#
# # 将Django的ASGI应用包装在Socket.IO的ASGI应用中
# application = ASGIApp(sio, get_asgi_application())


# ---------------------------------django-channels------------------------------------
import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from chat.routing import websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aiueoServer.settings')
django.setup()
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})

# application = get_asgi_application()
