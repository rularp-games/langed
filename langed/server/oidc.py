"""
OIDC/Keycloak utilities for authentication.
"""
import logging
from django.core.exceptions import SuspiciousOperation
from django.shortcuts import redirect
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from mozilla_django_oidc.views import OIDCAuthenticationCallbackView

logger = logging.getLogger('mozilla_django_oidc')


class SafeOIDCCallbackView(OIDCAuthenticationCallbackView):
    """
    Custom OIDC callback view that handles expired/invalid state gracefully.
    Instead of showing an error page, redirects to the login page to restart auth flow.
    """
    
    def get(self, request):
        try:
            return super().get(request)
        except SuspiciousOperation as e:
            # State not found in session - likely expired or tab was in background too long
            logger.warning(f"OIDC callback state error (redirecting to login): {e}")
            # Redirect to OIDC authenticate to restart the flow
            return redirect('oidc_authentication_init')


def generate_username(claims):
    """
    Generate a username from Keycloak claims.
    Uses 'preferred_username' from Keycloak token claims.
    Falls back to email or subject ID if preferred_username is not available.
    """
    # Try preferred_username first (standard Keycloak claim)
    if 'preferred_username' in claims:
        return claims['preferred_username']
    
    # Fallback to email
    if 'email' in claims:
        return claims['email'].split('@')[0]
    
    # Last resort: use the subject ID
    return claims.get('sub', '')


class KeycloakOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    """
    Custom OIDC authentication backend for Keycloak.
    """
    
    def filter_users_by_claims(self, claims):
        """Find user by Keycloak sub (unique ID) or username."""
        logger.debug(f"filter_users_by_claims called with: {claims}")
        
        sub = claims.get('sub')
        username = generate_username(claims)
        email = claims.get('email', '')
        
        # Try to find by username first
        users = self.UserModel.objects.filter(username=username)
        if users.exists():
            logger.debug(f"Found user by username: {username}")
            return users
        
        # Try to find by email
        if email:
            users = self.UserModel.objects.filter(email=email)
            if users.exists():
                logger.debug(f"Found user by email: {email}")
                return users
        
        logger.debug(f"No existing user found for: {username} / {email}")
        return self.UserModel.objects.none()
    
    def create_user(self, claims):
        """Create a new user from Keycloak claims."""
        logger.debug(f"create_user called with: {claims}")
        
        username = generate_username(claims)
        email = claims.get('email', '')
        first_name = claims.get('given_name', '')
        last_name = claims.get('family_name', '')
        
        user = self.UserModel.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        
        logger.info(f"Created new user: {username}")
        return user
    
    def update_user(self, user, claims):
        """Update existing user with latest Keycloak claims."""
        logger.debug(f"update_user called for: {user.username}")
        
        user.email = claims.get('email', user.email)
        user.first_name = claims.get('given_name', user.first_name)
        user.last_name = claims.get('family_name', user.last_name)
        user.save()
        
        logger.debug(f"Updated user: {user.username}")
        return user
    
    def verify_claims(self, claims):
        """Verify the claims are valid."""
        logger.debug(f"verify_claims called with: {claims}")
        
        # Check that we have required claims
        if not claims.get('sub'):
            logger.error("Missing 'sub' claim")
            return False
        
        return True

