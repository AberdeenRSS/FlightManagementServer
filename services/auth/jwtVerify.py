import requests
from quart import g, json
import jwt
from jwt import PyJWKClient
from cryptography.hazmat.primitives import serialization
from quart import current_app
from os import environ

azure_keys_jwk_client = None

jwt_audience = environ.get('FLIGHT_MANAGEMENT_SERVER_JWT_AUDIENCE')

def get_azure_public_keys_jwk_client():
    global azure_keys_jwk_client
    if azure_keys_jwk_client is None:
        client = PyJWKClient('https://login.microsoftonline.com/common/discovery/keys')
        client.get_signing_keys()
        azure_keys_jwk_client = client

    return azure_keys_jwk_client

def try_decode_token(token):

    token_headers = jwt.get_unverified_header(token)
    token_alg = token_headers['alg']
    token_kid = token_headers['kid']

    jwtPublicKeyClient = get_azure_public_keys_jwk_client()

    public_key = jwtPublicKeyClient.get_signing_key_from_jwt(token)

    audience = jwt_audience or current_app.config["audience"]

    decoded = jwt.decode(
        token, 
        public_key.key,
        [token_alg],
        audience=f'api://{audience}'
    )

    return decoded