
from datetime import datetime, timezone
from io import BytesIO
import math
import time
from typing import Iterable, Optional, cast
import uuid
from itertools import groupby
from app.helper.measurement_binary_helper import parse_binary_measurements
from fastapi import APIRouter, HTTPException, Request
from app.middleware.auth.requireAuth import AuthOptional, AuthRequired, verify_role
from app.models.flight_measurement import FlightMeasurement, FlightMeasurementSeriesIdentifier, getConcreteMeasurementSchema
from app.models.flight import FLIGHT_DEFAULT_HEAD_TIME, FLIGHT_MINIMUM_HEAD_TIME, Flight
from app.models.flight_measurement_compact import FlightMeasurementCompact, FlightMeasurementCompactDB, to_compact_db
from app.services.auth.permission_service import has_flight_permission
from app.services.data_access.flight import get_flight, create_or_update_flight
from app.services.data_access.flight_data_compact import get_flight_data_in_range, insert_flight_data as insert_flight_data_compact, get_aggregated_flight_data as get_aggregated_flight_data_compact, resolutions
from app.services.data_access.vessel import get_vessel
from app.controller.flight_controller import flights_controller
from fastapi import Query

flight_data_controller = APIRouter(
    prefix="/flight_data",
    tags=["flight_data"],
    dependencies=[],
)

@flights_controller.post("/{flight_id}/data/binary")
@flight_data_controller.post("/report_binary/{flight_id}")
async def report_binary(flight_id: uuid.UUID, request: Request, user: AuthRequired):
    """
    Method to report flight data for multiple parts
    This is meant to be called by a vessel.
    The vessel needs to tell the server which flight this data is for as well as
    which part of the vessel the data is for.
    ---
    Most efficient variant of the method allowing transmitting in raw binary format
    """

    verify_role(user, 'vessel')

    measurements = await request.body()

    flight = await get_flight(flight_id)

    if flight is None:
        raise HTTPException(404, f'Flight {flight_id} does not exist')
    
    # parsed = FlightMeasurementCompactSchema().load_list_safe(FlightMeasurementCompact, parsed_data)

    after_parse_time = time.time()

    measured_parts = flight.measured_parts

    # In case the end of the flight is coming near extend it
    if flight.end is not None and (flight.end.timestamp() - datetime.now(timezone.utc).timestamp()) < FLIGHT_MINIMUM_HEAD_TIME.total_seconds():
        flight.end = datetime.now(timezone.utc) + FLIGHT_DEFAULT_HEAD_TIME
        flight.end = flight.end.replace(tzinfo=timezone.utc)
        await create_or_update_flight(flight)

    db_measurements = list[FlightMeasurementCompactDB]()

    parsed_measurements = parse_binary_measurements(BytesIO(measurements), flight)

    for m in parsed_measurements:
        
        if str(m.part_id) not in measured_parts:
            return f'A measurement for part {m.part_id} cannot be stored, because the part was previously not specified to be measured in the flight', 400

        db_measurements.append(to_compact_db(m.model_dump(by_alias=True)))

    after_to_compact_time = time.time()
       
    await insert_flight_data_compact(db_measurements, flight_id)

    after_db_time = time.time()

    return 'success'


@flights_controller.post("/{flight_id}/data/compact")
@flight_data_controller.post("/report_compact/{flight_id}")
async def report_flight_data_compact(flight_id: uuid.UUID, measurements: list[FlightMeasurementCompact], user: AuthRequired):
    """
    Method to report flight data for multiple parts
    This is meant to be called by a vessel.
    The vessel needs to tell the server which flight this data is for as well as
    which part of the vessel the data is for. The data needs to be transmitted as
    a list of FlightMeasurement. A flight measurement contains the datetime the
    measurement is for as well as a dictionary of the measured values. Note that
    the measured values and datatypes need to be previously registered correctly
    when creating the flight, through setting the measured parts array
    """

    verify_role(user, 'vessel')

    start_time = time.time()

    flight = await get_flight(flight_id)

    after_flight_time = time.time()

    if flight is None:
        raise HTTPException(404, f'Flight {flight_id} does not exist')
    
    # parsed = FlightMeasurementCompactSchema().load_list_safe(FlightMeasurementCompact, parsed_data)

    after_parse_time = time.time()

    measured_parts = flight.measured_parts

    # In case the end of the flight is coming near extend it
    if flight.end is not None and (flight.end.timestamp() - datetime.now(timezone.utc).timestamp()) < FLIGHT_MINIMUM_HEAD_TIME.total_seconds():
        flight.end = datetime.now(timezone.utc) + FLIGHT_DEFAULT_HEAD_TIME
        flight.end = flight.end.replace(tzinfo=timezone.utc)
        await create_or_update_flight(flight)

    db_measurements = list[FlightMeasurementCompactDB]()

    for m in measurements:
        
        if str(m.part_id) not in measured_parts:
            return f'A measurement for part {m.part_id} cannot be stored, because the part was previously not specified to be measured in the flight', 400

        db_measurements.append(to_compact_db(m.model_dump(by_alias=True)))

    after_to_compact_time = time.time()
       
    await insert_flight_data_compact(db_measurements, flight_id)

    after_db_time = time.time()

    return 'success'

@flights_controller.get("/{flight_id}/data")
async def get_flight_data(user:AuthOptional,flight_data:uuid.UUID,vessel_part:uuid.UUID=Query(),start:str=Query(),end:str=Query(),resolution:Optional[str]=Query(default=None)):
    if resolution:
        return await get_aggregated(flight_data, vessel_part, resolution, start, end, user)
    else:
        return await getRange(flight_data, vessel_part, start, end, user)

@flight_data_controller.get("/get_aggregated_range/{flight_id}/{vessel_part}/{resolution}/{start}/{end}")
async def get_aggregated(flight_id: uuid.UUID, vessel_part: uuid.UUID, resolution: str, start: str, end: str, user: AuthOptional) -> list[FlightMeasurementCompactDB]:
    """
    Gets flight measurements for a specific part within the specified range at a specified resolution
    The flight data returned by this method is aggregated at a higher resolution. The avg, min and
    max of the data will be produced efficiently on the server and returned. This method should be
    used if a large range of data is required.
    """

    if resolution not in resolutions:
        raise HTTPException(400, f'{resolution} is not supported')

    series_identifier = FlightMeasurementSeriesIdentifier(_flight_id = flight_id, _vessel_part_id= vessel_part)

    flight = await get_flight(flight_id)

    if flight is None:
        raise HTTPException(404, 'Flight does not exist')
    
    vessel = await get_vessel(flight.vessel_id)

    if vessel is None:
        raise HTTPException(404, 'Vessel does not exist')
    
    if not has_flight_permission(flight, vessel, 'read', user):
        raise HTTPException(403, 'You don\'t have the required permission to access the flight')

    measured_parts = cast(dict, flight.measured_parts)

    # If the part is not part of this flight, there are no
    # values available
    if str(vessel_part) not in measured_parts:
        return list()
    
    measurement_schema = measured_parts[str(vessel_part)]
    
    values = await get_aggregated_flight_data_compact(series_identifier, datetime.fromisoformat(start), datetime.fromisoformat(end), resolution, measurement_schema) # type: ignore

    return values

@flight_data_controller.get("/get_range/{flight_id}/{vessel_part}/{start}/{end}")
async def getRange(flight_id: uuid.UUID, vessel_part: uuid.UUID, start: str, end: str, user: AuthOptional) -> list[FlightMeasurementCompactDB]:
    """
    Gets flight measurements for a specific part within the specified range.
    """

    series_identifier = FlightMeasurementSeriesIdentifier(_flight_id = flight_id, _vessel_part_id=vessel_part)

    if start.endswith('Z'):
        start = start[:-1]
    if end.endswith('Z'):
        end = end[:-1]

    flight = await get_flight(flight_id)

    if flight is None:
        raise HTTPException(404, 'Flight does not exist')
    
    vessel = await get_vessel(flight.vessel_id)

    if vessel is None:
        raise HTTPException(404, 'Vessel does not exist')
    
    if not has_flight_permission(flight, vessel, 'read', user):
        raise HTTPException(403, 'You don\'t have the required permission to access the flight')

    measured_parts = cast(dict, flight.measured_parts)

    # If the part is not part of this flight, there are no
    # values available
    if str(vessel_part) not in measured_parts:
        return list()
    
    values = await get_flight_data_in_range(series_identifier, datetime.fromisoformat(start), datetime.fromisoformat(end))

    return values
