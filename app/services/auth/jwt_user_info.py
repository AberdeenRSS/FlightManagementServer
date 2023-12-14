from typing import Any, Union

class UserInfo:
    # A unique id of the user
    _id: str

    roles: list[str]

    name: Union[str, None]

    token: dict[str, Any]

socket_users = dict[str, UserInfo]()

def user_from_token(raw_token: dict) -> UserInfo:
    user = UserInfo()
    user._id = raw_token['uid']
    user.name = raw_token.get('name')
    user.token = raw_token
    user.roles = raw_token.get('roles') or list()

    return user
    
def set_socket_user_info(user: UserInfo, sid: str):

    global socket_users

    socket_users[sid] = user

def get_socket_user_info(sid: str) -> Union[UserInfo, None]:
    """
    Retrieves the user information from the global context if available
    """

    global socket_users

    if sid is None:
        return None
    
    if sid in socket_users:
        return socket_users[sid]
    
    return None

def require_socket_user_info(sid: str) -> UserInfo:

    user = get_socket_user_info(sid)

    if user is None:
        raise Exception('Unauthorized')
    
    return user
