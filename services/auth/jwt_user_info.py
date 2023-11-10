from typing import Any, Union
from quart import g, request

class User:
    # A unique id of the user
    _id: str

    roles: list[str]

    name: Union[str, None]

    token: dict[str, Any]

socket_users = dict[str, User]()
    
def set_user_info(raw_token: dict[str, Any], sid: Union[str, None] = None):

    global socket_users

    user = User()
    user._id = raw_token['uid']
    user.name = raw_token.get('name')
    user.token = raw_token
    user.roles = raw_token.get('roles') or list()

    if sid is not None:  # type: ignore
        socket_users[sid] = user # type: ignore
    else:
        g.rss_jwt_user = user

def get_user_info(sid: Union[str,None]=None) -> Union[User, None]:
    """
    Retrieves the user information from the global context if available
    """

    global socket_users

    if sid is not None:
        if sid in socket_users:
            return socket_users[sid]
        return None

    if 'rss_jwt_user' in g:
        return g.rss_jwt_user
   
    return None