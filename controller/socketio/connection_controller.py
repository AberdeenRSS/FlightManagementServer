from logging import Logger
from typing import Coroutine, cast
from socketio import Server
from middleware.auth.requireAuth import try_authenticate_socket

from services.auth.jwt_user_info import User, get_user_info

def init_connection_controller(sio: Server, logger: Logger):

    @sio.event
    async def connect(sid, environ, auth):

        # Auth currently disabled
        return

        error_msg = try_authenticate_socket(sid, auth)

        if error_msg != None:

            logger.critical(f'Client authentication failed: {error_msg}')
            await cast(Coroutine, sio.disconnect(sid))

            return False

        # user = cast(User, get_user_info(sid))

        # logger.info(f'Successfully established websocket connection {user.token["email"] if "email" in user.token else "" } ({user.unique_id})')
