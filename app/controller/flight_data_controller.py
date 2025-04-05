
from datetime import datetime
from typing import Optional, cast
import uuid
from fastapi import APIRouter, HTTPException
from app.middleware.auth.requireAuth import AuthOptional
from app.models.flight_measurement import FlightMeasurementAggregated, FlightMeasurementSeriesIdentifier
from app.models.flight_measurement import FlightMeasurementDB
from app.services.auth.permission_service import has_flight_permission
from app.services.data_access.flight import get_flight
from app.services.data_access.flight_data import get_aggregated_flight_data as get_aggregated_flight_data_individual, get_flight_data_in_range, resolutions
from app.services.data_access.vessel import get_vessel
from app.controller.flight_controller import flights_controller
from fastapi import Query

flight_data_controller = APIRouter(
    prefix="/flight_data",
    tags=["flight_data"],
    dependencies=[],
)

@flights_controller.get("/{flight_id}/data")
async def get_flight_data(user:AuthOptional,flight_data:uuid.UUID,vessel_part:uuid.UUID=Query(), series_name:str=Query(),start:str=Query(),end:str=Query(),resolution:Optional[str]=Query(default=None)):
    if resolution:
        return await get_aggregated(flight_data, vessel_part, series_name, resolution, start, end, user)
    else:
        return await getRange(flight_data, vessel_part, start, end, user)

@flight_data_controller.get("/get_aggregated_range/{flight_id}/{vessel_part}/{series_name}/{resolution}/{start}/{end}")
async def get_aggregated(flight_id: uuid.UUID, vessel_part: uuid.UUID, series_name: str, resolution: str, start: str, end: str, user: AuthOptional) -> list[FlightMeasurementAggregated]:
    """
    Gets flight measurements for a specific part within the specified range at a specified resolution
    The flight data returned by this method is aggregated at a higher resolution. The avg, min and
    max of the data will be produced efficiently on the server and returned. This method should be
    used if a large range of data is required.
    """

    if start.endswith('Z'):
        start = start[:-1]
    if end.endswith('Z'):
        end = end[:-1]

    if resolution not in resolutions:
        raise HTTPException(400, f'{resolution} is not supported')

    flight = await get_flight(flight_id)

    if flight is None:
        raise HTTPException(404, 'Flight does not exist')
    
    vessel = await get_vessel(flight.vessel_id)

    if vessel is None:
        raise HTTPException(404, 'Vessel does not exist')
    
    if not has_flight_permission(flight, vessel, 'read', user):
        raise HTTPException(403, 'You don\'t have the required permission to access the flight')

    measured_parts = flight.measured_parts

    vessel_part_str = str(vessel_part)
    
    i = 0
    for id in measured_parts:
        if id == vessel_part_str:
            break
        i += 1

    if i >= len(measured_parts):
        return list()

    measurement_schema = measured_parts[str(vessel_part)]

    j = 0
    for descriptor in measurement_schema:
        if descriptor.name == series_name:
            break
        j += 1

    if j >= len(measurement_schema):
        return list()

    values = await get_aggregated_flight_data_individual(flight_id, i, j, datetime.fromisoformat(start), datetime.fromisoformat(end), resolution, measurement_schema) # type: ignore

    for v in values:
        v.part_id = uuid.UUID(flight.measured_part_ids[v.p_index])
        v.series_name = measurement_schema[v.m_index].name

    return values

@flight_data_controller.get("/get_range/{flight_id}/{vessel_part}/{start}/{end}")
async def getRange(flight_id: uuid.UUID, vessel_part: uuid.UUID, start: str, end: str, user: AuthOptional) -> list[FlightMeasurementDB]:
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
