from typing import cast
from flask import Blueprint
from flask import request, flash, g, jsonify
from middleware.auth.requireAuth import auth_required
from uuid import uuid4

from flasgger import swag_from

from models.flight import Flight, FlightSchema
from services.auth.jwt_user_info import User, get_user_info
from services.data_access.flight import create_or_update_flight, get_all_flights_for_vessels, get_flight
from services.data_access.vessel import get_vessel


flight_controller = Blueprint('flight', __name__, url_prefix='/flight')

# Method for a vessel to register
@flight_controller.route("/create", methods = ['POST'])
@auth_required
def create_flight():
    """
    Creates a flight
    ---
    responses:
      200:
        description: The flight how it has been saved in the database
        schema:
          $ref: "#/definitions/Flight"
    """

    flight = FlightSchema().load_safe(Flight, request.get_json())
    user_info = cast(User, get_user_info())

    # Create a new random uuid for the flight
    flight._id = uuid4()

    # Load the vessel to ensure it exists and to get its current version
    vessel = get_vessel(str(flight._vessel_id))

    if vessel is None:
        flash(f'Vessel {flight._vessel_id} does not exist yet. Please create the vessel before creating a flight for it')
        return ''
    
    if str(vessel._id) != user_info.unique_id:
        flash(f'Vessel does not belong to current user. Only the vessel itself can create a flight')
        return ''

    # Assign the correct version
    flight._vessel_version = vessel._version

    acc = create_or_update_flight(flight)

    return FlightSchema().dumps(acc)

@flight_controller.route("/get_all/<vessel_id>", methods = ['GET'])
@auth_required
def get_all(vessel_id):
    """
    Fetches all flights that the passed vessel ever performed
    ---
    responses:
      200:
        description: All flights
        schema:
          type: array
          items:
            $ref: "#/definitions/Flight"
    """

    flights = get_all_flights_for_vessels(str(vessel_id))
    return FlightSchema(many=True).dumps(flights)

