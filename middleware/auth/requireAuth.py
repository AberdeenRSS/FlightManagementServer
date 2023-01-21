from functools import wraps
from typing import Union
from flask import request, flash, current_app, session
from flask_socketio import disconnect

from services.auth.jwtVerify import try_decode_token
from services.auth.jwt_user_info import get_user_info, set_user_info

def try_authenticate_http() -> Union[str, None]:
    # If already authenticated in this context, return
    if get_user_info() != None:
        return None

    token = None

    if 'x-access-tokens' in request.headers:
        token = request.headers['x-access-tokens']
    if 'Authorization' in request.headers:
        token = request.headers['Authorization']

    if not token:
        return 'a valid token is missing'

    if token.startswith('Bearer '):
        token = token.replace('Bearer ', '')

    return try_authenticate(token)

def try_authenticate_socket() -> Union[str, None]:

    # If already authenticated in this context, return
    if get_user_info() != None:
        return None

    if not request.event:  # type: ignore
        return 'Authorization attempted outside handshake'

    if 'args' not in request.event:  # type: ignore
        return 'Authorization attempted outside handshake'

    token = None

    for e in request.event['args']:  # type: ignore
        if 'token' in e:
            token = e['token']

    if not token:  # type: ignore
        return 'No token found in handshake args'

    return try_authenticate(token)  # type: ignore


def try_authenticate(token: str) -> Union[str, None]:
    """Tries to get a bearer token form the request and run authentication. If the auth
    challenge succeeds the user information is filled out if not returns a reason
    why the authentication failed
    """
    
    try:
        decoded_token = try_decode_token(token)
        set_user_info(decoded_token)
    except:
        return 'token is invalid'
    return None

def auth_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):

        error_msg = try_authenticate_http()
        if error_msg:
            flash(error_msg)
    
        return f(*args, **kwargs)
    return decorator

def socket_authenticated_only(f):
    @wraps(f)
    def wrapped(*args, **kwargs):

        error = try_authenticate_socket()

        if error != None:
            current_app.logger.info('Unauthorized request, disconnected client')
            disconnect()
        else:
            return f(*args, **kwargs)
    return wrapped