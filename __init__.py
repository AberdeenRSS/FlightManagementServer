from flask import Flask, logging
from flask_cors import CORS
from controller.socketio.connection_controller import init_connection_controller
from controller.socketio.init import init_socket_io_controller
from services.data_access.init import init_data_access
from services.data_access.mongodb.mongodb_connection import init_app
from controller.vessel_controller import vessel_api
from controller.flight_controller import flight_controller
from controller.flight_data_controller import flight_data_controller
from controller.command_controller import command_controller
from flask_socketio import SocketIO
from services.swagger.init_swagger import init_swagger
from os import environ

def create_app(debug=False):

    # Init db
    init_data_access()

    # create app
    app = Flask(__name__)

    if debug:
        app.logger.setLevel('DEBUG')
    else:
        app.logger.setLevel('INFO')


    # Set default config (should come from env later)
    app.config['audience'] = environ.get('FLIGHT_MANAGEMENT_SERVER_JWT_AUDIENCE')
    app.config['connection_string'] = environ.get('FLIGHT_MANAGEMENT_SERVER_CONNECTION_STRING')
    app.config['CORS_HEADERS'] = 'Content-Type'
    app.config['SECRET_KEY'] = 'secret!'

    # Configure cross origin requests
    CORS(app)
    CORS(vessel_api)
    CORS(flight_controller)
    CORS(flight_data_controller)

    init_app(app)

    # Register controllers
    app.register_blueprint(vessel_api)
    app.register_blueprint(flight_controller)
    app.register_blueprint(flight_data_controller)
    app.register_blueprint(command_controller)


    socketio = SocketIO(app, cors_allowed_origins = '*')
    init_socket_io_controller(socketio)

    init_swagger(app)

    app.logger.info('Started server')

    return (app, socketio)
