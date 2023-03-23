from socketio import Server
from controller.socketio.connection_controller import init_connection_controller
from controller.socketio.flight_controller import init_flight_controller
from controller.socketio.flight_data_controller import init_flight_data_controller
from controller.socketio.command_controller import init_command_controller


def init_socket_io_controller(socketio: Server):
    init_connection_controller(socketio)
    init_flight_data_controller(socketio)
    init_command_controller(socketio)
    init_flight_controller(socketio)