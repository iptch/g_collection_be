import logging
import re
from django.http import HttpRequest
import requests
import jwt

from .crypto import rsa_pem_from_jwk
from .models import User

from rest_framework import authentication
from rest_framework import exceptions

logger = logging.getLogger(__name__)


class AzureVerifyTokenError(Exception):
    pass


class InvalidAuthorizationToken(AzureVerifyTokenError):
    def __init__(self, details=''):
        super().__init__(f'Invalid authorization token: {details}')


class JWTAccessTokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request: HttpRequest):
        regex_bearer = re.compile(r'^[Bb]earer (.*)$')
        valid_audience = 'api://ae04e6aa-6cb5-4c16-9d3b-45bd6a79845c'
        issue = 'https://sts.windows.net/a9080dcf-8589-4cb6-a2e2-21398dc6c671/'
        jwks_uri = 'https://login.microsoftonline.com/a9080dcf-8589-4cb6-a2e2-21398dc6c671/discovery/v2.0/keys'

        # Extract header
        header_authorization_value = request.headers.get('authorization')
        if not header_authorization_value:
            raise exceptions.AuthenticationFailed("Authorization header is not present")
        # Extract supposed raw JWT
        match = regex_bearer.match(header_authorization_value)
        if not match:
            raise exceptions.AuthenticationFailed("Authorization header must start with Bearer followed by its token")
        raw_jwt = match.groups()[-1]
        decoded_token = self.verify_jwt(token=raw_jwt,
                        valid_audiences=[valid_audience],
                        issuer=issue,
                        jwks_uri=jwks_uri,
                        verify=True, )
        
        current_user: User = User.objects.get(email=decoded_token["unique_name"])
        return current_user, self

    def verify_jwt(self,
                   token,
                   valid_audiences,
                   jwks_uri,
                   issuer,
                   verify=True
                   ):
        public_key = self.get_public_key(token=token, jwks_uri=jwks_uri)
        try:
            decoded = jwt.decode(
                token,
                public_key,
                verify=verify,
                algorithms=['RS256'],
                audience=valid_audiences,
                issuer=issuer
            )
        except jwt.exceptions.PyJWTError as exc:
            raise InvalidAuthorizationToken(exc.__class__.__name__)
        else:
            return decoded

    def get_public_key(self, token, jwks_uri):
        kid = self.get_kid(token)
        jwk = self.get_jwk(kid=kid, jwks_uri=jwks_uri)
        return rsa_pem_from_jwk(jwk)

    @staticmethod
    def get_kid(token):
        headers = jwt.get_unverified_header(token)
        if not headers:
            raise InvalidAuthorizationToken('headers missing')
        try:
            return headers['kid']
        except KeyError:
            raise InvalidAuthorizationToken('kid missing from headers')

    @staticmethod
    def get_jwk(kid, jwks_uri):
        resp = requests.get(jwks_uri)
        if not resp.ok:
            raise AzureVerifyTokenError(
                f'Received {resp.status_code} response code from {jwks_uri}'
            )
        try:
            jwks = resp.json()
        except (ValueError, TypeError):
            raise AzureVerifyTokenError(
                f'Received malformed response from {jwks_uri}'
            )
        for jwk in jwks.get('keys'):
            if jwk.get('kid') == kid:
                return jwk
        raise InvalidAuthorizationToken('kid not recognized')