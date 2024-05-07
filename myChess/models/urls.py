from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import ChessGameViewSet

router = DefaultRouter()
router.register(r'games', ChessGameViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
