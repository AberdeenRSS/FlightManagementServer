from flask import Blueprint
from flask import request, flash, g, jsonify
from helper.model_helper import export_list
from middleware.auth.requireAuth import auth_required
from uuid import uuid4

from models.flight import Flight
from services.auth.jwt_user_info import get_user_info
from services.data_access.flight import create_or_update_flight, get_all_flights_for_vessels, get_flight
from services.data_access.vessel import get_vessel


flight_controller = Blueprint('flight', __name__, url_prefix='/flight')

# Method for a vessel to register
@flight_controller.route("/create", methods = ['POST'])
@auth_required
def create_flight():

    flight = Flight(request.get_json())
    user_info = get_user_info()

    # Create a new random uuid for the flight
    flight._id = uuid4()

    # Load the vessel to ensure it exists and to get its current version
    vessel = get_vessel(str(flight._vessel_id))

    if vessel is None:
        flash(f'Vessel {flight._vessel_id} does not exist yet. Please create the vessel before creating a flight for it')
        return
    
    if str(vessel._id) != user_info.unique_id:
        flash(f'Vessel does not belong to current user. Only the vessel itself can create a flight')
        return

    # Use the identity of the user as the vessel, as safety
    flight._vessel_version = vessel._version

    flight.validate()

    acc = create_or_update_flight(flight)

    return jsonify(acc.to_primitive())

@flight_controller.route("/get_all/<vessel_id>", methods = ['GET'])
@auth_required
def get_all(vessel_id):

    vessels = get_all_flights_for_vessels(str(vessel_id))
    return jsonify(export_list(vessels))

