
import asyncio
from datetime import datetime, timezone
import math
import time
from typing import Iterable, Tuple, Union, cast
import uuid
from quart import Blueprint
from quart import request, flash, g, jsonify, current_app
from middleware.auth.requireAuth import auth_required
from models.flight_measurement import FlightMeasurement, FlightMeasurementAggregatedSchema, FlightMeasurementSchema, FlightMeasurementSeriesIdentifier, FlightMeasurementSeriesIdentifierSchema, getConcreteMeasurementSchema
from itertools import groupby

from models.flight import FLIGHT_DEFAULT_HEAD_TIME, FLIGHT_MINIMUM_HEAD_TIME, FlightSchema
from models.command import CommandSchema
from models.flight_measurement_compact import FlightMeasurementCompact, FlightMeasurementCompactDB, FlightMeasurementCompactDBSchema, FlightMeasurementCompactSchema, to_compact_db

from services.auth.jwt_user_info import User, get_user_info
from services.data_access.command import get_commands_in_range
from services.data_access.flight import get_flight, create_or_update_flight
from services.data_access.flight_data_compact import get_flight_data_in_range, insert_flight_data as insert_flight_data_compact, get_aggregated_flight_data as get_aggregated_flight_data_compact, resolutions


flight_data_controller = Blueprint('flight_data', __name__, url_prefix='/flight_data')

@flight_data_controller.route("/report/<flight_id>/<vessel_part>", methods = ['POST'])
@auth_required
async def report_flight_data(flight_id: str, vessel_part: str):
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

    # user_info = cast(User, get_user_info())
    flight = await get_flight(flight_id)

    if flight is None:
        return f'Flight {flight_id}', 400

    # if str(flight._vessel_id) != user_info.unique_id:
    #     return f'Only the vessel itself is allowed to report flight data', 401

    measured_parts = cast(dict, flight.measured_parts)

    if vessel_part not in measured_parts:
        return f'A measurement for part {vessel_part} cannot be stored, because the part was previously not specified to be measured in the flight', 400
    
    measurement_schema = getConcreteMeasurementSchema(measured_parts[vessel_part])
    
    parsed_data = await request.get_json()

    if not parsed_data or not isinstance(parsed_data, Iterable):
        return 'Invalid json (not an array)', 400
    
    # In case the end of the flight is coming near extend it
    if flight.end is not None and (flight.end - datetime.utcnow()) < FLIGHT_MINIMUM_HEAD_TIME:
        flight.end = datetime.utcnow() + FLIGHT_DEFAULT_HEAD_TIME
        flight.end = flight.end.replace(tzinfo=timezone.utc)
        await create_or_update_flight(flight)

    # Import the measurements with the specified schema
    measurements = measurement_schema().load_list_safe(FlightMeasurement, parsed_data)

    await insert_flight_data_compact(measurements, flight_id)

    return jsonify({'success': True})

@flight_data_controller.route("/report/<flight_id>", methods = ['POST'])
@auth_required
async def report_flight_data_combined(flight_id: str):
    """
    Method to report flight data for multiple parts
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

    # user_info = cast(User, get_user_info())
    flight = await get_flight(flight_id)

    if flight is None:
        return f'Flight {flight_id}', 400

    # if str(flight._vessel_id) != user_info.unique_id:
    #     return f'Only the vessel itself is allowed to report flight data', 401

    parsed_data = await request.get_json()

    if parsed_data is None or not isinstance(parsed_data, Iterable):
        return 'Invalid json (not an array)', 400
    
    parsed_data = cast(list[dict], parsed_data)
    
    if len(parsed_data) < 1:
        return '', 200
    
    for d in parsed_data:
        if not isinstance(d, dict):
            return 'Measurements not in dictionary format', 400
        if 'part_id' not in d:
            return 'part_id needs to be provided for each measurement when using combined method', 400
    
    # In case the end of the flight is coming near extend it
    if flight.end is not None and (flight.end - datetime.now(timezone.utc)) < FLIGHT_MINIMUM_HEAD_TIME:
        flight.end = datetime.utcnow() + FLIGHT_DEFAULT_HEAD_TIME
        flight.end = flight.end.replace(tzinfo=timezone.utc)
        await create_or_update_flight(flight)

    grouped = groupby(parsed_data, lambda k: cast(str, cast(dict, k)['part_id']))

    measured_parts = flight.measured_parts

    measurements_to_save = list()
    for part_id, g in grouped:

        if part_id not in measured_parts:
            return f'A measurement for part {part_id} cannot be stored, because the part was previously not specified to be measured in the flight', 400
        
        measurement_schema = getConcreteMeasurementSchema(measured_parts[part_id])

        measurements = measurement_schema().load_list_safe(FlightMeasurement, g)

        measurements_to_save.extend(measurements)

    await insert_flight_data_compact(measurements_to_save, flight_id)

    return jsonify({'success': True})

@flight_data_controller.route("/report_compact/<flight_id>", methods = ['POST'])
@auth_required
async def report_flight_data_compact(flight_id: str):
    """
    Method to report flight data for multiple parts
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
        description: The id of the flight the data is reported for\
      - name: body
        required: true
        in: body
        schema:
          type: array
          items:
            $ref: "#/definitions/FlightMeasurementCompact"
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

    start_time =  time.time()

    flight = await get_flight(flight_id)

    after_flight_time = time.time()

    if flight is None:
        return f'Flight {flight_id}', 400

    parsed_data = await request.get_json()

    if parsed_data is None or not isinstance(parsed_data, Iterable):
        return 'Invalid json (not an array)', 400
    
    # parsed = FlightMeasurementCompactSchema().load_list_safe(FlightMeasurementCompact, parsed_data)

    after_parse_time = time.time()

    measured_parts = flight.measured_parts

    # In case the end of the flight is coming near extend it
    if flight.end is not None and (flight.end - datetime.now(timezone.utc)) < FLIGHT_MINIMUM_HEAD_TIME:
        flight.end = datetime.utcnow() + FLIGHT_DEFAULT_HEAD_TIME
        flight.end = flight.end.replace(tzinfo=timezone.utc)
        await create_or_update_flight(flight)

    db_measurements = list[FlightMeasurementCompactDB]()

    for part in parsed_data:

        part_id_as_str = str(part['part_id'])
        
        if part_id_as_str not in measured_parts:
            return f'A measurement for part {part["part_id"]} cannot be stored, because the part was previously not specified to be measured in the flight', 400

        db_measurements.append(to_compact_db(part))

    after_to_compact_time = time.time()
       
    await insert_flight_data_compact(db_measurements, flight_id)

    after_db_time = time.time()

    current_app.logger.info(f'Took {math.ceil((after_db_time-start_time)*1000)}ms in total: {math.ceil((after_flight_time-start_time)*1000)}ms loading flight; {math.ceil((after_parse_time-after_flight_time)*1000)}ms parsing; {math.ceil((after_to_compact_time-after_parse_time)*1000)}ms prepare; {math.ceil((after_db_time-after_to_compact_time)*1000)}ms db')

    return jsonify({'success': True})


@flight_data_controller.route("/get_aggregated_range/<flight_id>/<vessel_part>/<resolution>/<start>/<end>", methods = ['GET'])
@auth_required
async def get_aggregated(flight_id: str, vessel_part: str, resolution: str, start: str, end: str):
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
        return f'{resolution} is not supported', 400

    series_identifier = FlightMeasurementSeriesIdentifier(_flight_id = uuid.UUID(flight_id), _vessel_part_id= uuid.UUID(vessel_part))

    flight = await get_flight(flight_id)

    if not flight:
        return 'Flight does not exist', 404

    measured_parts = cast(dict, flight.measured_parts)

    # If the part is not part of this flight, there are no
    # values available
    if vessel_part not in measured_parts:
        return jsonify(list())
    
    measurement_schema = measured_parts[vessel_part]
    
    values = await get_aggregated_flight_data_compact(series_identifier, datetime.fromisoformat(start), datetime.fromisoformat(end), resolution, measurement_schema) # type: ignore

    return FlightMeasurementCompactDBSchema(many=True).dumps(values)

@flight_data_controller.route("/get_range/<flight_id>/<vessel_part>/<start>/<end>", methods = ['GET'])
@auth_required
async def getRange(flight_id: str, vessel_part: str, start: str, end: str):
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

    flight = await get_flight(flight_id)

    if not flight:
        return 'Flight does not exist', 404

    measured_parts = cast(dict, flight.measured_parts)

    # If the part is not part of this flight, there are no
    # values available
    if vessel_part not in measured_parts:
        return jsonify(list())
    
    values = await get_flight_data_in_range(series_identifier, datetime.fromisoformat(start), datetime.fromisoformat(end))

    return FlightMeasurementCompactDBSchema(many=True).dumps(values)
