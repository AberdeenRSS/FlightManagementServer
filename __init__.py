from quart import Quart
from quart_cors import cors
from controller.socketio.connection_controller import init_connection_controller
from controller.socketio.init import init_socket_io_controller
from middleware.logging.request_logging import use_request_logging
from services.data_access.init import init_data_access
from services.data_access.mongodb.mongodb_connection import init_app
from controller.vessel_controller import vessel_api
from controller.flight_controller import flight_controller
from controller.flight_data_controller import flight_data_controller
from controller.command_controller import command_controller
from services.swagger.init_swagger import init_swagger
from os import environ
import socketio

def create_app(debug=False):

    # Init db
    init_data_access()

    # create app
    app = Quart(__name__)

    if debug:
        app.logger.setLevel('DEBUG')
    else:
        app.logger.setLevel('INFO')


    # Set default config (should come from env later)
    app.config['audience'] = environ.get('FLIGHT_MANAGEMENT_SERVER_JWT_AUDIENCE')
    app.config['connection_string'] = environ.get('FLIGHT_MANAGEMENT_SERVER_CONNECTION_STRING')
    app.config['CORS_HEADERS'] = 'Content-Type'
    app.config['SECRET_KEY'] = 'secret!'

    app = cors(app, allow_origin='*')

    # Configure cross origin requests
    # CORS(app)
    # CORS(vessel_api)
    # CORS(flight_controller)
    # CORS(flight_data_controller)

    use_request_logging(app)

    init_app(app)

    # Register controllers
    app.register_blueprint(cors(vessel_api, allow_origin='*'))
    app.register_blueprint(flight_controller)
    app.register_blueprint(flight_data_controller)
    app.register_blueprint(command_controller)


    # socketio = SocketIO(app, cors_allowed_origins = '*')

    socketio_server = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

    init_socket_io_controller(socketio_server, app.logger)

    # init_swagger(app)


    app.logger.info('Started server')

    return (app, socketio_server)
