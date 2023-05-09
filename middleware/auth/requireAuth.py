from functools import wraps
from typing import TypeVar, Union
from quart import request, flash, current_app, session
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

def try_authenticate_socket(sid: str, auth: Union[dict[str, str], None] = None) -> Union[str, None]:

    # If already authenticated in this context, return
    if get_user_info(sid) != None:
        return None
    
    if auth is None:
        return 'Authentication handshake did not happen yet'

    # Try to get the token out of the auth dict
    token = None

    if 'token' in auth:
        token = auth['token']

    if token is None or token == '':
        return 'No token found in handshake args'

    return try_authenticate(token, sid)


def try_authenticate(token: str, sid: Union[str, None] = None) -> Union[str, None]:
    """Tries to get a bearer token form the request and run authentication. If the auth
    challenge succeeds the user information is filled out if not returns a reason
    why the authentication failed
    """
    
    try:
        decoded_token = try_decode_token(token)
        set_user_info(decoded_token, sid)
    except:
        return 'token is invalid'
    return None

def auth_required(f):
    @wraps(f)
    async def decorator(*args, **kwargs):

        error_msg = try_authenticate_http()
        if error_msg:
            return error_msg, 401
    
        return await f(*args, **kwargs)
    return decorator

def socket_authenticated_only(f):
    @wraps(f)
    def wrapped(*args, **kwargs):

        sid: str = args[0] # get the socket id of the client (always the first parameter of the wrapped method)

        error = try_authenticate_socket(sid)

        if error != None:
            # current_app.logger.info('Unauthorized request, disconnected client')
            disconnect()
        else:
            return f(*args, **kwargs)
    return wrapped


def role_required(role: str):
    def d(f):
        @wraps(f)
        async def decorator(*args, **kwargs):

            user = get_user_info()

            if user is None:
                return  401
            
            if role not in user.roles:
                return 403
            
            return await f(*args, **kwargs)
        return decorator
    return d
    
def role_required_socket(role: str):

    def d(f):
        @wraps(f)
        async def decorator(*args, **kwargs):

            sid: str = args[0] # get the socket id of the client (always the first parameter of the wrapped method)

            user = get_user_info(sid)

            if user is None:
                return 401
            
            if role not in user.roles:
                return 403
            
            return await f(*args, **kwargs)
        return decorator

    return d