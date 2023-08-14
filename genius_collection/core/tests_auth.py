from genius_collection.core.jwt_validation import JWTAccessTokenAuthentication


# for local debugging only
def test_verify_jwt():
    valid_audience = 'api://ae04e6aa-6cb5-4c16-9d3b-45bd6a79845c'
    azure_ad_issuer = 'https://sts.windows.net/a9080dcf-8589-4cb6-a2e2-21398dc6c671/'
    azure_ad_jwks_uri = 'https://login.microsoftonline.com/a9080dcf-8589-4cb6-a2e2-21398dc6c671/discovery/v2.0/keys'

    jwt_to_verify = '<enter a valid jwt here>'
    authenticator = JWTAccessTokenAuthentication()
    payload = authenticator.verify_jwt(
        token=jwt_to_verify,
        valid_audiences=[valid_audience],
        issuer=azure_ad_issuer,
        jwks_uri=azure_ad_jwks_uri,
        verify=True,
    )
    print(payload)
