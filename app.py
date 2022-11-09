from flask import Flask
from flask_cors import CORS
from services.data_access.init import init_data_access
from services.data_access.mongodb.mongodb_connection import init_app
from controller.vessel_controller import vessel_api
from controller.flight_controller import flight_controller
from controller.flight_data_controller import flight_data_controller


# Init db
init_data_access()

# create app
app = Flask(__name__)

# Set default config (should come from env later)
app.config['client_id'] = 'dffc1b9f-47ce-4ba4-a925-39c61eab50ba'
app.config['CORS_HEADERS'] = 'Content-Type'

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
