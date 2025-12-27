"""
OIDC/Keycloak utilities for authentication.
"""


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

