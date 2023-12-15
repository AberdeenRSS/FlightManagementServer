import datetime
from functools import lru_cache
import cryptography
import jwt
import time

from app.config import get_settings
from ...models.authorization_code import AuthorizationCode, generate_auth_code
from ...models.user import User, hash_password

ISSUER = 'rss-flight-server'
LIFE_SPAN = 60*60*24
LIFE_SPAN_REFRESH = 60*60*24*30

@lru_cache
def get_private_key():

  settings = get_settings()

  with open(settings.auth_private_key_path, 'rb') as f:
    private_key = f.read().decode()

  return private_key

@lru_cache
def get_public_key():

  cryptography.__builtins__

  settings = get_settings()

  with open(settings.auth_public_key_path, 'rb') as f:
    public_key = f.read().decode()
    
  return public_key


def generate_access_token(user: User):
  payload = {
    "iss": ISSUER,
    "exp": time.time() + LIFE_SPAN,
    "name": user.name,
    "unique_name": user.unique_name,
    "uid": str(user.id),
    "roles": user.roles
  }

  access_token = jwt.encode(payload, get_private_key(), algorithm = 'RS256')

  return access_token

def generate_refresh_token(user: User):
  return AuthorizationCode(_id=generate_auth_code(265), corresponding_user=user.id, single_use=True, valid_until=datetime.datetime.fromtimestamp(time.time() + LIFE_SPAN_REFRESH, tz=datetime.timezone.utc))

def validate_access_token(token: str):
  return jwt.decode(token, get_public_key(), algorithms=['RS256'], issuer=ISSUER, options={"require": ["exp", "iss"]}, verify=True)