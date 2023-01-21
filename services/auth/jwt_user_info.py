from typing import Any, Union
from flask import g, request

socket_users = dict()

class User:
    # A unique id of the user
    unique_id: str

    user_type: str = 'human'

    name: Union[str, None]

    token: dict[str, Any]

    
def set_user_info(raw_token: dict[str, Any]):

    global socket_users

    user = User()
    user.unique_id = raw_token['sub']
    user.token = raw_token

    if hasattr(request, 'sid'):  # type: ignore
        socket_users[request.sid] = user # type: ignore

    g.rss_jwt_user = user

def get_user_info() -> Union[User, None]:
    """
    Retrieves the user information from the global context if available
    """
    if 'rss_jwt_user' in g:
        return g.rss_jwt_user
    if hasattr(request, 'sid') and request.sid in socket_users:  # type: ignore
        return socket_users[request.sid]  # type: ignore
    return None