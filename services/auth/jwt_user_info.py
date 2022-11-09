from typing import Any, Union
from flask import g

class User:
    # A unique id of the user
    unique_id: str

    user_type: Union['human', 'script'] = 'human'

    name: Union[str, None]

    token: dict[str, Any]

    
def set_user_info(raw_token: dict[str, Any]):
    user = User()
    user.unique_id = raw_token['sub']
    user.token = raw_token
    g.rss_jwt_user = user

def get_user_info() -> Union[User, None]:
    if 'rss_jwt_user' in g:
        return g.rss_jwt_user
    return None