from typing import cast
from quart import Blueprint
from quart import request, flash, g, jsonify
from middleware.auth.requireAuth import auth_required, role_required, use_auth
from uuid import uuid4
from datetime import datetime, timedelta

from flasgger import swag_from

from models.flight import Flight, FlightSchema, FLIGHT_DEFAULT_HEAD_TIME
from services.auth.jwt_user_info import User, get_user_info
from services.auth.permission_service import has_flight_permission, modify_flight_permission
from services.data_access.flight import create_or_update_flight, get_all_flights_for_vessels, get_all_flights_for_vessels_by_name, get_flight
from services.data_access.user import get_user_by_unique_name
from services.data_access.vessel import get_vessel 


flight_controller = Blueprint('flight', __name__, url_prefix='/flight')

# Method for a vessel to register
@flight_controller.route("/create", methods = ['POST'])
@auth_required
@role_required('vessel')
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

    # Create a new random uuid for the flight
    flight._id = uuid4()

    flight.start = datetime.utcnow()

    flight.end = datetime.utcnow() + FLIGHT_DEFAULT_HEAD_TIME

    # Load the vessel to ensure it exists and to get its current version
    vessel = await get_vessel(str(flight._vessel_id))

    if vessel is None:
        return f'Vessel {flight._vessel_id} does not exist yet. Please create the vessel before creating a flight for it', 400
        
    flight._vessel_version = vessel._version

    acc = await create_or_update_flight(flight)

    return FlightSchema().dumps(acc)

@flight_controller.route("/get_all/<vessel_id>", methods = ['GET'])
@use_auth
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

    vessel = await get_vessel(vessel_id)

    if vessel is None:
        return 'Vessel does not exist', 404

    flights = await get_all_flights_for_vessels(str(vessel_id))
    return FlightSchema(many=True).dumps([f for f in flights if has_flight_permission(f, vessel, 'view')])

@flight_controller.route("/get_by_name/<vessel_id>/<name>", methods = ['GET'])
@use_auth
async def get_by_name(vessel_id, name):
    '''
    Fetches all flights with the specified name
    '''

    vessel = await get_vessel(vessel_id)

    if vessel is None:
        return 'Vessel does not exist', 404
    
    flights = await get_all_flights_for_vessels_by_name(str(vessel_id), name)
    return FlightSchema(many=True).dumps([f for f in flights if has_flight_permission(f, vessel, 'view')])

@flight_controller.route('/set_permission/<flight_id>/<unique_user_name>/<permission>')
@use_auth
async def set_permission(flight_id: str, unique_user_name: str, permission: str):

    flight = await get_flight(flight_id)

    if flight is None:
        return 'Flight does not exist', 404
    
    vessel = await get_vessel(str(flight._vessel_id))

    if vessel is None:
        return 'Vessel does not exist', 404
    
    if not has_flight_permission(flight, vessel, 'owner'):
        return 'You don\'t have the required permission to access the flight', 403
  
    other_user = await get_user_by_unique_name(unique_user_name)

    if other_user is None:
        return 'User you are trying to give permission to does not exist', 400
    
    modify_flight_permission(flight, permission, other_user._id)

    await create_or_update_flight(flight)

    return 'success', 200