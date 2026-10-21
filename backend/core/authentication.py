import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

_jwks_client = jwt.PyJWKClient(settings.KEYCLOAK_JWKS_URL, cache_jwk_set=True, lifespan=300)

class TokenUser:
    is_authenticated = True
    is_active = True
    def __init__(self, payload):
        self.sub = payload['sub']
        self.username = payload.get('preferred_username', self.sub)
        self.email = payload.get('email', '')
        self.roles = payload.get('realm_access', {}).get('roles', [])
    def __str__(self):
        return self.username

class KeycloakJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = request.headers.get('Authorization', '')
        if not header:
            return None
        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise AuthenticationFailed('Expected Bearer token')
        try:
            key = _jwks_client.get_signing_key_from_jwt(parts[1]).key
            payload = jwt.decode(
                parts[1], key, algorithms=['RS256'],
                audience=settings.KEYCLOAK_AUDIENCE,
                issuer=settings.KEYCLOAK_ISSUER,
                options={'require': ['exp', 'iss', 'sub', 'aud']},
            )
        except (jwt.PyJWTError, jwt.PyJWKClientError, ValueError) as exc:
            raise AuthenticationFailed('Invalid or expired access token') from exc
        return (TokenUser(payload), payload)
    def authenticate_header(self, request):
        return 'Bearer realm="rag-app"'
