# ---------------------------------django-channels------------------------------------
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'chat/channel/(?P<conv_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
]
