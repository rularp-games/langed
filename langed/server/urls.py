from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    GameViewSet, RunViewSet, ConventionViewSet, ConventionEventViewSet,
    CityViewSet, ConventionLinkViewSet, VenueViewSet, RoomViewSet, current_user, auth_urls
)

router = DefaultRouter()
router.register(r'games', GameViewSet, basename='game')
router.register(r'runs', RunViewSet, basename='run')
router.register(r'conventions', ConventionViewSet, basename='convention')
router.register(r'convention-events', ConventionEventViewSet, basename='convention-event')
router.register(r'cities', CityViewSet, basename='city')
router.register(r'venues', VenueViewSet, basename='venue')
router.register(r'rooms', RoomViewSet, basename='room')
router.register(r'convention-links', ConventionLinkViewSet, basename='convention-link')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/user/', current_user, name='current-user'),
    path('auth/urls/', auth_urls, name='auth-urls'),
]
