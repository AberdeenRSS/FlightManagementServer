from typing import cast
from socketio import Server
from middleware.auth.requireAuth import try_authenticate_socket

from services.auth.jwt_user_info import User, get_user_info

def init_connection_controller(sio: Server):

    @sio.event
    def connect(sid, environ, auth):

        error_msg = try_authenticate_socket(sid, auth)

        if error_msg != None:
            # current_app.logger.critical(f'Client authentication failed: {error_msg}')
            sio.disconnect(sid)
            return False

        user = cast(User, get_user_info(sid))

        # current_app.logger.info(f'Successful websocket connection {user.token["email"] if "email" in user.token else "" } ({user.unique_id})')
