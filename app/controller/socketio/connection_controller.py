from logging import Logger
from typing import Coroutine, cast
from socketio import Server
from app.middleware.auth.requireAuth import try_authenticate_socket

from app.services.auth.jwt_user_info import UserInfo, get_socket_user_info

def init_connection_controller(sio: Server, logger: Logger | None):

    @sio.event
    async def connect(sid, environ, auth):

        error_msg = try_authenticate_socket(sid, auth)

        if error_msg != None:

            if logger is not None:
                logger.critical(f'Client authentication failed: {error_msg}')
            await cast(Coroutine, sio.disconnect(sid))

            return False

        user = cast(UserInfo, get_socket_user_info(sid))

        if logger is not None:
            logger.info(f'Successfully established websocket connection {user.name} ({user._id}) ')
