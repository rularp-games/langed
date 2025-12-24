from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GameViewSet, RunViewSet, ConventionViewSet, ConventionEventViewSet

router = DefaultRouter()
router.register(r'games', GameViewSet, basename='game')
router.register(r'runs', RunViewSet, basename='run')
router.register(r'conventions', ConventionViewSet, basename='convention')
router.register(r'convention-events', ConventionEventViewSet, basename='convention-event')

urlpatterns = [
    path('', include(router.urls)),
]
