from pathlib import Path

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'example_secret_key'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

ALLOWED_HOSTS = ['*']

# Keycloak OIDC settings
# Replace these values with your Keycloak configuration
KEYCLOAK_SERVER_URL = 'keycloak.example.com'  # e.g., 'https://keycloak.example.com'
KEYCLOAK_REALM = 'my-realm'  # e.g., 'my-realm'

OIDC_RP_CLIENT_ID = 'keycloak-client-id'  # Client ID from Keycloak
OIDC_RP_CLIENT_SECRET = 'keycloak-client-secret'  # Client secret from Keycloak

# Keycloak endpoints (auto-generated from server URL and realm)
OIDC_OP_AUTHORIZATION_ENDPOINT = f'{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/auth'
OIDC_OP_TOKEN_ENDPOINT = f'{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token'
OIDC_OP_USER_ENDPOINT = f'{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/userinfo'
OIDC_OP_JWKS_ENDPOINT = f'{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs'
OIDC_OP_LOGOUT_ENDPOINT = f'{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/logout'

# CSRF trusted origins - add your domain here
# Example: ['https://langed.example.com', 'https://www.langed.example.com']
CSRF_TRUSTED_ORIGINS = ['localhost']

# Site URL for OIDC callback
SITE_URL = 'localhost'

# OIDC Redirect URL - must match what's configured in Keycloak
OIDC_REDIRECT_URL = f'{SITE_URL}/oidc/callback/'

# Session cookie security - set to False for local HTTP development
# In production (HTTPS), this should be True
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

