from typing import cast
from quart import Blueprint
from quart import request, flash, g, jsonify
from middleware.auth.requireAuth import auth_required, role_required
from uuid import uuid4
from datetime import datetime, timedelta

from flasgger import swag_from

from models.flight import Flight, FlightSchema, FLIGHT_DEFAULT_HEAD_TIME
from services.auth.jwt_user_info import User, get_user_info
from services.data_access.flight import create_or_update_flight, get_all_flights_for_vessels, get_flight
from services.data_access.vessel import get_vessel


flight_controller = Blueprint('flight', __name__, url_prefix='/flight')

# Method for a vessel to register
@flight_controller.route("/create", methods = ['POST'])
@auth_required
@role_required('Access.Vessel')
async def create_flight():
    """
    Creates a flight
    ---
    parameters:
      - name: 'body'
        in: 'body'
        description: 'Json object containing information about the flight that are supposed to be created'
        schema:
          $ref: "#/definitions/Flight"
    responses:
      200:
        description: The flight how it has been saved in the database
        schema:
          $ref: "#/definitions/Flight"
      400:
        description: Returned if the vessel does not exist that the flight is created for
      401: 
        description: Returned if the user creating the vessel is not a vessel themselves
    """

    flight = FlightSchema().load_safe(Flight, await request.get_json(), partial=True)
    user_info = cast(User, get_user_info())

    # Create a new random uuid for the flight
    flight._id = uuid4()

    flight.start = datetime.utcnow()

    flight.end = datetime.utcnow() + FLIGHT_DEFAULT_HEAD_TIME

    # Load the vessel to ensure it exists and to get its current version
    vessel = await get_vessel(str(flight._vessel_id))

    if vessel is None:
        return f'Vessel {flight._vessel_id} does not exist yet. Please create the vessel before creating a flight for it', 400
        
    if str(vessel._id) != user_info.unique_id:
        return f'Vessel does not belong to current user. Only the vessel itself can create a flight', 401

    # Assign the correct version
    flight._vessel_version = vessel._version

    acc = await create_or_update_flight(flight)

    return FlightSchema().dumps(acc)

@flight_controller.route("/get_all/<vessel_id>", methods = ['GET'])
@auth_required
async def get_all(vessel_id):
    """
    Fetches all flights that the passed vessel ever performed
    ---
    parameters:
      - name: vessel_id
        required: true
        in: path
        type: string
        description: The id of the vessel to get the flights for
    responses:
      200:
        description: All flights
        schema:
          type: array
          items:
            $ref: "#/definitions/Flight"
    """

    flights = await get_all_flights_for_vessels(str(vessel_id))
    return FlightSchema(many=True).dumps(flights)

