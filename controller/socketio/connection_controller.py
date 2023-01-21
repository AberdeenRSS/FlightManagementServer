from typing import cast
from flask_socketio import SocketIO
from flask_socketio import disconnect
from flask import current_app
from middleware.auth.requireAuth import try_authenticate_socket

from services.auth.jwt_user_info import User, get_user_info

def init_connection_controller(socketio: SocketIO):

    @socketio.on('connect')
    def connect():

        error_msg = try_authenticate_socket()

        if error_msg != None:
            current_app.logger.critical(f'Client authentication failed: {error_msg}')
            disconnect()
            return

        user = cast(User, get_user_info())

        current_app.logger.info(f'Successful websocket connection {user.token["email"] if "email" in user.token else "" } ({user.unique_id})')
