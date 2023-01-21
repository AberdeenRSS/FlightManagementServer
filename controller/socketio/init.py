from flask_socketio import SocketIO
from controller.socketio.connection_controller import init_connection_controller
from controller.socketio.flight_data_controller import init_flight_data_controller


def init_socket_io_controller(socketio: SocketIO):
    init_connection_controller(socketio)
    init_flight_data_controller(socketio)