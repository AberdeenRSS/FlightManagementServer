from datetime import datetime
from typing import cast
import uuid
from flask import Blueprint
from flask import request, flash, g, jsonify
from middleware.auth.requireAuth import auth_required
from models.flight_measurement import FlightMeasurement, FlightMeasurementSchema, FlightMeasurementSeriesIdentifier, FlightMeasurementSeriesIdentifierSchema, getConcreteMeasurementSchema

from models.flight import FlightSchema
from services.auth.jwt_user_info import User, get_user_info
from services.data_access.flight import get_flight, create_or_update_flight
from services.data_access.flight_data import insert_flight_data, get_flight_data_in_range, get_aggregated_flight_data, resolutions


flight_data_controller = Blueprint('flight_data', __name__, url_prefix='/flight_data')

# Method for a vessel to register
@flight_data_controller.route("/report/<flight_id>/<vessel_part>", methods = ['POST'])
@auth_required
def report_flight_data(flight_id: str, vessel_part: str):
    """
    Method to report flight data. This is meant to be called by a vessel.
    The vessel needs to tell the server which flight this data is for as well as
    which part of the vessel the data is for. The data needs to be transmitted as
    a list of FlightMeasurement. A flight measurement contains the datetime the
    measurement is for as well as a dictionary of the measured values. Note that
    the measured values and datatypes need to be previously registered correctly
    when creating the flight, through setting the measured parts array
    """

    user_info = cast(User, get_user_info())
    flight = get_flight(flight_id)

    if flight is None:
        flash(f'Flight {flight_id}')
        return ''

    if str(flight._vessel_id) != user_info.unique_id:
        flash(f'Only the vessel itself is allowed to report flight data')
        return ''

    measured_parts = cast(dict, flight.measured_parts)

    if vessel_part not in measured_parts:
        flash(f'A measurement for part {vessel_part} cannot be stored, because the part was previously not specified to be measured in the flight')
    
    measurement_schema = getConcreteMeasurementSchema(measured_parts[vessel_part])
    
    parsed_data = request.get_json()

    if not parsed_data or not isinstance(parsed_data, list):
        flash('Invalid json')
        return ''

    # Import the measurements with the specified schema
    measurements = measurement_schema().load_list_safe(FlightMeasurement, parsed_data)

    insert_flight_data(measurements, flight_id, vessel_part)

    return jsonify({'success': True})

@flight_data_controller.route("/get_range/<flight_id>/<vessel_part>/<start>/<end>", methods = ['GET'])
@auth_required
def get_range(flight_id: str, vessel_part: str, start: str, end: str):

    series_identifier = FlightMeasurementSeriesIdentifier(_flight_id = uuid.UUID(flight_id), _vessel_part_id= uuid.UUID(vessel_part))

    if start.endswith('Z'):
        start = start[:-1]
    if end.endswith('Z'):
        end = end[:-1]

    values = get_flight_data_in_range(series_identifier, datetime.fromisoformat(start), datetime.fromisoformat(end))

    return jsonify(FlightMeasurementSchema().dump_list(values))

@flight_data_controller.route("/get_aggregated_range/<flight_id>/<vessel_part>/<resolution>/<start>/<end>", methods = ['GET'])
@auth_required
def get_aggregated(flight_id: str, vessel_part: str, resolution: str, start: str, end: str):

    if resolution not in resolutions:
        flash(f'{resolution} is not supported')

    series_identifier = FlightMeasurementSeriesIdentifier(_flight_id = uuid.UUID(flight_id), _vessel_part_id= uuid.UUID(vessel_part))

    if start.endswith('Z'):
        start = start[:-1]
    if end.endswith('Z'):
        end = end[:-1]

    flight = get_flight(flight_id)

    if not flight:
        flash('Flight does not exist')
        return ''

    measured_parts = cast(dict, flight.measured_parts)

    # If the part is not part of this flight, there are no
    # values available
    if vessel_part not in measured_parts:
        return jsonify(list())
    
    measurement_schema = measured_parts[vessel_part]
    
    values = get_aggregated_flight_data(series_identifier, datetime.fromisoformat(start), datetime.fromisoformat(end), resolution, measurement_schema)

    return jsonify(values)


