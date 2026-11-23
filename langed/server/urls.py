from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    GameViewSet, RunViewSet, ConventionViewSet, ConventionEventViewSet,
    CityViewSet, ConventionLinkViewSet, VenueViewSet, RoomViewSet, 
    auth_urls, search_users
)
from .auth_api import (
    CurrentUserView, ProvidersView, LoginView, RegisterView, PasswordResetView, PasswordChangeView, LogoutView
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
    path('auth/user/', CurrentUserView.as_view(), name='current-user'),
    path('auth/urls/', auth_urls, name='auth-urls'),
    path('auth/providers/', ProvidersView.as_view(), name='auth-providers'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/password-reset/', PasswordResetView.as_view(), name='auth-password-reset'),
    path('auth/password-change/', PasswordChangeView.as_view(), name='auth-password-change'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('users/search/', search_users, name='search-users'),
]
