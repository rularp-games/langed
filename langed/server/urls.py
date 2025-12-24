from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GameViewSet, RunViewSet

router = DefaultRouter()
router.register(r'games', GameViewSet, basename='game')
router.register(r'runs', RunViewSet, basename='run')

urlpatterns = [
    path('', include(router.urls)),
]

