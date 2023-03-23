from typing import Any, Union
from quart import g, request

socket_users = dict()

class User:
    # A unique id of the user
    unique_id: str

    user_type: str = 'human'

    name: Union[str, None]

    token: dict[str, Any]

    
def set_user_info(raw_token: dict[str, Any], sid: Union[str, None] = None):

    global socket_users

    user = User()
    user.unique_id = raw_token['sub']
    user.token = raw_token

    if sid is not None:  # type: ignore
        socket_users[sid] = user # type: ignore
    else:
        g.rss_jwt_user = user

def get_user_info(sid: Union[str,None]=None) -> Union[User, None]:
    """
    Retrieves the user information from the global context if available
    """

    if sid is not None:
        if sid in socket_users:
            return socket_users[sid]
        return None

    if 'rss_jwt_user' in g:
        return g.rss_jwt_user
   
    return None