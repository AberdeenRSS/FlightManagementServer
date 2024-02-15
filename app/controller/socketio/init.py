from logging import Logger
from socketio import Server
from app.controller.socketio.connection_controller import init_connection_controller
from app.controller.socketio.flight_controller import init_flight_controller
from app.controller.socketio.flight_data_controller import init_flight_data_controller
from app.controller.socketio.command_controller import init_command_controller


def init_socket_io_controller(socketio: Server, logger: Logger | None = None):
    init_connection_controller(socketio, logger)
    init_flight_data_controller(socketio, logger)
    init_command_controller(socketio, logger)
    init_flight_controller(socketio, logger)