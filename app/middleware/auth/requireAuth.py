from functools import wraps
from typing import Annotated, Union
import inspect
from fastapi import Depends, HTTPException, Header
from socketio import Server
from ...services.auth.jwt_auth_service import validate_access_token
from ...services.auth.jwt_user_info import UserInfo, get_socket_user_info, set_socket_user_info, user_from_token

def try_get_bearer(x_access_token: Annotated[str | None, Header(alias='Authorization')] = None) -> Union[str, None]:

    if x_access_token is None:
        return None
    
    if x_access_token.startswith('Bearer '):
        x_access_token = x_access_token.replace('Bearer ', '')

    return x_access_token

def user_optional(bearer: Annotated[str | None, Depends(try_get_bearer)]) -> Union[UserInfo, None]:
    '''Returns "None" if successful, otherwise returns string with rejection reason'''

    if bearer is None:
        return None

    return get_user_from_bearer(bearer)

def user_required(bearer: Annotated[str | None, Depends(try_get_bearer)]) -> UserInfo:

    if bearer is None:
        raise HTTPException(401, 'Missing bearer token')
    
    return get_user_from_bearer(bearer)

AuthOptional = Annotated[UserInfo, Depends(user_optional)]
AuthRequired = Annotated[UserInfo, Depends(user_required)]

def verify_role(user_info: UserInfo, role: str):

    if role not in user_info.roles:
        raise HTTPException(403, f'Access denied, requires role: {role}')

def try_authenticate_socket(sid: str, auth: Union[dict[str, str], None] = None) -> Union[str, None]:

    # If already authenticated in this context, return
    if get_socket_user_info(sid) != None:
        return None
    
    if auth is None:
        return 'Authentication handshake did not happen yet'

    # Try to get the token out of the auth dict
    token = None

    if 'token' in auth:
        token = auth['token']

    if token is None or token == '':
        return 'No token found in handshake args'

    user = get_user_from_bearer(token)

    set_socket_user_info(user, sid)

def get_user_from_bearer(token: str) -> UserInfo:
    """Tries to get a bearer token form the request and run authentication. If the auth
    challenge succeeds the user information is filled out if not returns a reason
    why the authentication failed
    """
    
    try:
        decoded_token = validate_access_token(token)
        return user_from_token(decoded_token)
    except Exception as err:
        raise HTTPException(401, err.args[0])


def socket_authenticated_only(sio: Server):

    def decorator(f):

        @wraps(f)
        async def wrapped(*args, **kwargs):
        
            sid: str = args[0] # get the socket id of the client (always the first parameter of the wrapped method)

            error = try_authenticate_socket(sid)

            if error is not None :
                # current_app.logger.info('Unauthorized request, disconnected client')
                sio.disconnect(sid)
            else:
                res = f(*args, **kwargs)

                if inspect.iscoroutine(res) or inspect.iscoroutinefunction(res):
                    return await res
                return res
        return wrapped
    
    return decorator

def socket_use_auth(sio: Server):
    '''Fails only on invalid token but not on no token'''

    def decorator(f):
        @wraps(f)
        async def wrapped(*args, **kwargs):
        
            sid: str = args[0] # get the socket id of the client (always the first parameter of the wrapped method)

            error = try_authenticate_socket(sid)

            if error is not None and error != 'No token found in handshake args':
                # current_app.logger.info('Unauthorized request, disconnected client')
                sio.disconnect(sid)
            else:
                res = f(*args, **kwargs)

                if inspect.iscoroutine(res) or inspect.iscoroutinefunction(res):
                    return await res
                return res
        return wrapped

    return decorator

    
def role_required_socket(role: str):

    def d(f):
        @wraps(f)
        async def decorator(*args, **kwargs):

            res = f(*args, **kwargs)

            if inspect.iscoroutine(res) or inspect.iscoroutinefunction(res):
                return await res
            return res

            sid: str = args[0] # get the socket id of the client (always the first parameter of the wrapped method)

            user = get_socket_user_info(sid)

            if user is None:
                return 401
            
            if role not in user.roles:
                return 403
            
            return await f(*args, **kwargs)
        return decorator

    return d