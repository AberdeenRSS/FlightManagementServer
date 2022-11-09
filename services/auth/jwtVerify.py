import requests
from flask import g, json
import jwt
from jwt import PyJWKClient
from cryptography.hazmat.primitives import serialization

azure_public_keys_client = 'azure_public_keys_client'
audience = 'api://dffc1b9f-47ce-4ba4-a925-39c61eab50ba'

azure_keys_jwk_client = None

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

    decoded = jwt.decode(
        token, 
        public_key.key,
        [token_alg],
        audience=audience
    )

    return decoded