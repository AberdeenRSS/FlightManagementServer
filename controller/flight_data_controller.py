from datetime import datetime
from flask import Blueprint
from flask import request, flash, g, jsonify
from helper.model_helper import export_list, import_list
from middleware.auth.requireAuth import auth_required
from models.flight_measurement import FlightMeasurement, FlightMeasurementSeriesIdentifier, getConcreteMeasurementSchema

from models.flight import Flight
from services.auth.jwt_user_info import get_user_info
from services.data_access.flight import get_flight, create_or_update_flight
from services.data_access.flight_data import insert_flight_data, get_flight_data_in_range, get_aggregated_flight_data, resolutions


flight_data_controller = Blueprint('flight_data', __name__, url_prefix='/flight_data')

# Method for a vessel to register
@flight_data_controller.route("/report/<flight_id>/<vessel_part>", methods = ['POST'])
@auth_required
def report_Flight_data(flight_id: str, vessel_part: str):

    user_info = get_user_info()
    flight = get_flight(flight_id)

    if flight is None:
        flash(f'Flight {flight_id}')

    if str(flight._vessel_id) != user_info.unique_id:
        flash(f'Only the vessel itself is allowed to report flight data')

    if vessel_part not in flight.measured_parts:
        flash(f'A measurement for part {vessel_part} cannot be stored, because the part was previously not specified to be measured in the flight')
    
    measurement_schema = getConcreteMeasurementSchema(flight.measured_parts[vessel_part])
    
    # Import the measurements with the specified schema
    measurements = import_list(request.get_json(), measurement_schema)

    for measurement in measurements:
        # measurement._series = FlightMeasurementSeriesIdentifier({'_flight_id': flight_id, '_vessel_part_id': vessel_part})
        measurement.validate()

    insert_flight_data(measurements, flight_id, vessel_part)

    return jsonify({'success': True})

@flight_data_controller.route("/get_range/<flight_id>/<vessel_part>/<start>/<end>", methods = ['GET'])
@auth_required
def get_range(flight_id: str, vessel_part: str, start: str, end: str):

    series_identifier = FlightMeasurementSeriesIdentifier({'_flight_id': flight_id, '_vessel_part_id': vessel_part})

    if start.endswith('Z'):
        start = start[:-1]
    if end.endswith('Z'):
        end = end[:-1]

    values = get_flight_data_in_range(series_identifier, datetime.fromisoformat(start), datetime.fromisoformat(end))

    return jsonify(export_list(values))

@flight_data_controller.route("/get_aggregated_range/<flight_id>/<vessel_part>/<resolution>/<start>/<end>", methods = ['GET'])
@auth_required
def get_aggregated(flight_id: str, vessel_part: str, resolution: str, start: str, end: str):

    if resolution not in resolutions:
        flash(f'{resolution} is not supported')

    series_identifier = FlightMeasurementSeriesIdentifier({'_flight_id': flight_id, '_vessel_part_id': vessel_part})

    if start.endswith('Z'):
        start = start[:-1]
    if end.endswith('Z'):
        end = end[:-1]

    flight = get_flight(flight_id)

    # If the part is not part of this flight, there are no
    # values available
    if vessel_part not in flight.measured_parts:
        jsonify(list())
    
    measurement_schema = flight.measured_parts[vessel_part]
    
    values = get_aggregated_flight_data(series_identifier, datetime.fromisoformat(start), datetime.fromisoformat(end), resolution, measurement_schema)

    return jsonify(values)


