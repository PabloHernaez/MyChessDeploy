from django.urls import re_path
from .consumers import  ChessConsumer 

websocket_urlpatterns = [
    re_path(r'ws/play/(?P<gameID>\d+)/$', ChessConsumer.as_asgi()),
]
