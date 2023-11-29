import datetime
import cryptography
import jwt
import time
from models.authorization_code import AuthorizationCode, generate_auth_code
from models.user import User, hash_password

from services.data_access.user import get_user_by_unique_name

ISSUER = 'rss-flight-server'
LIFE_SPAN = 1800

with open('private.pem', 'rb') as f:
  private_key = f.read().decode()

with open('public.pem', 'rb') as f:
  public_key = f.read().decode()


def generate_access_token(user: User):
  payload = {
    "iss": ISSUER,
    "exp": time.time() + LIFE_SPAN,
    "name": user.name,
    "unique_name": user.unique_name,
    "uid": str(user._id)
  }

  access_token = jwt.encode(payload, private_key, algorithm = 'RS256')

  return access_token

def generate_refresh_token(user: User):
  return AuthorizationCode(generate_auth_code(265), user._id, True, datetime.datetime.fromtimestamp(time.time() + LIFE_SPAN))

def validate_access_token(token: str):
  return jwt.decode(token, public_key, algorithms=['RS256'], issuer=ISSUER, options={"require": ["exp", "iss"]}, verify=True)