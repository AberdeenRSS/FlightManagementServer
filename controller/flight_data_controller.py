from datetime import datetime
from typing import cast
import uuid
from flask import Blueprint
from flask import request, flash, g, jsonify
from middleware.auth.requireAuth import auth_required
from models.flight_measurement import FlightMeasurement, FlightMeasurementSchema, FlightMeasurementSeriesIdentifier, FlightMeasurementSeriesIdentifierSchema, getConcreteMeasurementSchema

from models.flight import FLIGHT_DEFAULT_HEAD_TIME, FLIGHT_MINIMUM_HEAD_TIME, FlightSchema
from models.command import CommandSchema

from services.auth.jwt_user_info import User, get_user_info
from services.data_access.command import get_commands_in_range
from services.data_access.flight import get_flight, create_or_update_flight
from services.data_access.flight_data import insert_flight_data, get_flight_data_in_range, get_aggregated_flight_data, resolutions

flight_data_controller = Blueprint('flight_data', __name__, url_prefix='/flight_data')

# Method for a vessel to register
@flight_data_controller.route("/report/<flight_id>/<vessel_part>", methods = ['POST'])
@auth_required
def report_flight_data(flight_id: str, vessel_part: str):
    """
    Method to report flight data. 
    This is meant to be called by a vessel.
    The vessel needs to tell the server which flight this data is for as well as
    which part of the vessel the data is for. The data needs to be transmitted as
    a list of FlightMeasurement. A flight measurement contains the datetime the
    measurement is for as well as a dictionary of the measured values. Note that
    the measured values and datatypes need to be previously registered correctly
    when creating the flight, through setting the measured parts array
    ---
    parameters:
      - name: flight_id
        required: true
        in: path
        type: string
        description: The id of the flight the data is reported for
      - name: vessel_part
        required: true
        in: path
        type: string
        description: The vessel part the data is coming from
      - name: body
        required: true
        in: body
        schema:
          type: array
          items:
            $ref: "#/definitions/FlightMeasurement"
        description: A list of measurements that is being reported
    responses:
      200:
        description: 
        schema:
          type: object
          properties:
            success: 
              type: boolean
      400:
        description: The flight the data is reported for does not yet exist or the measurement data was not in the expected format
      401:
        description: The user reporting the data was not the vessel
    """

    user_info = cast(User, get_user_info())
    flight = get_flight(flight_id)

    if flight is None:
        return f'Flight {flight_id}', 400

    if str(flight._vessel_id) != user_info.unique_id:
        return f'Only the vessel itself is allowed to report flight data', 401

    measured_parts = cast(dict, flight.measured_parts)

    if vessel_part not in measured_parts:
        return f'A measurement for part {vessel_part} cannot be stored, because the part was previously not specified to be measured in the flight', 400
    
    measurement_schema = getConcreteMeasurementSchema(measured_parts[vessel_part])
    
    parsed_data = request.get_json()

    if not parsed_data or not isinstance(parsed_data, list):
        return 'Invalid json (not an array)', 400
    
    # In case the end of the flight is coming near extend it
    if flight.end is not None and (flight.end - datetime.utcnow()) < FLIGHT_MINIMUM_HEAD_TIME:
        flight.end = datetime.utcnow() + FLIGHT_DEFAULT_HEAD_TIME
        create_or_update_flight(flight)

    # Import the measurements with the specified schema
    measurements = measurement_schema().load_list_safe(FlightMeasurement, parsed_data)

    insert_flight_data(measurements, flight_id, vessel_part)

    return jsonify({'success': True})

@flight_data_controller.route("/get_aggregated_range/<flight_id>/<vessel_part>/<resolution>/<start>/<end>", methods = ['GET'])
@auth_required
def get_aggregated(flight_id: str, vessel_part: str, resolution: str, start: str, end: str):
    """
    Gets flight measurements for a specific part within the specified range at a specified resolution
    The flight data returned by this method is aggregated at a higher resolution. The avg, min and
    max of the data will be produced efficiently on the server and returned. This method should be
    used if a large range of data is required.
    ---
    parameters:
      - name: flight_id
        required: true
        in: path
        type: string
        description: The id of the flight the measurements are requested for
      - name: vessel_part
        required: true
        in: path
        type: string
        description: The vessel part the measurements are requested for
      - name: resolution
        required: true
        in: path
        type: string
        description: The requested resolution. Can be 'decisecond', 'second', 'minute', 'hour', 'day' or 'month'
      - name: start
        required: true
        in: path
        type: string
        description: The start of the range
      - name: end
        required: true
        in: path
        type: string
        description: The end of the requested range
    responses:
      200:
        description: The measurements in the requested range
    """

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

@flight_data_controller.route("/get_range/<flight_id>/<vessel_part>/<start>/<end>", methods = ['GET'])
@auth_required
def getRange(flight_id: str, vessel_part: str, start: str, end: str):
    """
    Gets flight measurements for a specific part within the specified range.
    ---
    parameters:
      - name: flight_id
        required: true
        in: path
        type: string
        description: The id of the flight the measurements are requested for
      - name: vessel_part
        required: true
        in: path
        type: string
        description: The vessel part the measurements are requested for
      - name: start
        required: true
        in: path
        type: string
        description: The start of the range
      - name: end
        required: true
        in: path
        type: string
        description: The end of the requested range
    responses:
      200:
        description: The measurements in the requested range
    """


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
    
    values = get_flight_data_in_range(series_identifier, datetime.fromisoformat(start), datetime.fromisoformat(end))

    return jsonify(values)