from datetime import datetime, timezone
import json
from typing import Annotated, Optional, cast
from uuid import UUID
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.flight_measurement import FlightMeasurementAggregated, FlightMeasurementDB, FlightMeasurementSeriesIdentifier
from ..middleware.auth.requireAuth import AuthOptional, user_optional, user_required, verify_role
from jsonschema import validate, ValidationError
from app.models.command import Command
from app.models.flight import FLIGHT_MINIMUM_HEAD_TIME, FLIGHT_DEFAULT_HEAD_TIME
from app.services.auth.jwt_user_info import UserInfo
from app.services.auth.permission_service import has_flight_permission
from app.services.data_access.flight_data import get_aggregated_flight_data as get_aggregated_flight_data_individual, get_flight_data_in_range, resolutions
from app.services.data_access.flight import get_flight, create_or_update_flight
from app.services.data_access.vessel import get_vessel
from app.controller.flight_controller import flights_controller

command_controller = APIRouter(
    prefix="/command",
    tags=["command"],
    dependencies=[],
)

# @flights_controller.post("/{flight_id}/commands")
# @command_controller.post("/dispatch/{flight_id}")
# async def dispatch_commands(flight_id: UUID, commands: list[Command], user: Annotated[UserInfo, Depends(user_optional)]):
#     """
#     Dispatches a command to the vessel. Meant to be called from a ui/frontend or
#     other type of client
#     """

#     if len(commands) < 1:
#         raise HTTPException(400, 'Empty list of commands')

#     for command in commands:

#         command.create_time = cast(datetime, command.create_time.replace(tzinfo=timezone.utc))

#         try:
#             assert command.state == 'new'
#             assert command.create_time is not None
#             assert command.dispatch_time is None
#             assert command.receive_time is None
#             assert command.complete_time is None
#         except AssertionError as e:
#             raise HTTPException(400, f'Command {command.id} has wrong format: {e}')

#     flight = await get_flight(flight_id)

#     if flight is None:
#         raise HTTPException(400, 'Flight does not exist')
    
#     vessel = await get_vessel(flight.vessel_id)

#     if vessel is None:
#         raise HTTPException(400, 'Vessel does not exist')
    
#     if not has_flight_permission(flight, vessel, 'write', user):
#         raise HTTPException(403, 'You don\'t have write permission for this flight') 

#     for command in commands:
#         if command.command_type not in flight.available_commands:
#             raise HTTPException(400, f'Command {command.command_type} does not exist')
                
#         command_description = flight.available_commands[command.command_type]

#         if not command_description.supported_on_vehicle_level and command.part_id is None:
#             raise HTTPException(400, f'Command type {command.command_type} is not supported on vehicle level')

#         if command.part_id is not None and command.part_id not in command_description.supporting_parts:
#             raise HTTPException(400, f'Command type {command.command_type} not available for part {command.part_id}')

#         if command_description.payload_schema is None:
#             if command.command_payload is not None:
#                 raise HTTPException(400, f'Command {command.command_type} does not support a payload')
#             continue

#         if command.response is not None:
#             raise HTTPException(401, f'A response can only be send by the vessel')

#         try:
#             validate(command.command_payload, command_description.payload_schema)
#         except ValidationError:
#             raise HTTPException(400, f'Invalid payload for {command.id} (type: {command.command_type})')
        
#     # In case the end of the flight is coming near extend it
#     # if flight.end is not None and (flight.end - datetime.now(UTC)) < FLIGHT_MINIMUM_HEAD_TIME:
#     #     flight.end = datetime.now(UTC) + FLIGHT_DEFAULT_HEAD_TIME
#     #     await create_or_update_flight(flight)

#     await insert_commands(commands, flight_id, True)

#     return 'success'

# @flights_controller.post("/{flight_id}/commands/confirm")
# @command_controller.post("/confirm/{flight_id}")
# async def confirm_command(flight_id: UUID, commands: list[Command], user: Annotated[UserInfo, Depends(user_required)]):
#     """
#     To be called by the vessel to confirm the the receipt or the
#     processing of the command or that the vessel directly created a command
#     """

#     verify_role(user, 'vessel')

#     flight = await get_flight(flight_id)

#     if flight is None:
#         raise HTTPException(404, 'Unknown flight')

#     for command in commands:
#         try:
#             assert command.state != 'new'
#             assert command.create_time
#         except AssertionError:
#             raise HTTPException(400, f'Command {command.id} has wrong format')

#         if str(command.command_type) not in flight.available_commands:
#             raise HTTPException(400, f'Command {command.command_type} does not exist')
        
#         command_description = flight.available_commands[command.command_type]

#         if not command_description.supported_on_vehicle_level and command.part_id is None:
#             raise HTTPException(400, f'Command type {command.command_type} is not supported on vehicle level')

#         if command.part_id is not None and command.part_id not in command_description.supporting_parts:
#             raise HTTPException(400, f'Command type {command.command_type} not available for part {command.part_id}')
        
#         if command.command_payload is not None and command_description.payload_schema is None:
#             raise HTTPException(404, f'Command {command.command_type} does not support a payload')

#         if command_description.payload_schema is not None:

#             try:
#                 validate(command.command_payload, command_description.payload_schema)
#             except ValidationError:
#                 raise HTTPException(404, f'Invalid payload for {command.id} (type: {command.command_type})')
            
#         if command.response is not None and command_description.response_schema is None:
#             raise HTTPException(400, f'Command {command.command_type} does not support a response')

#         if command_description.response_schema is not None and command.command_payload is not None:

#             try:
#                 validate(command.response, command_description.response_schema)
#             except ValidationError:
#                 raise HTTPException(400, f'Invalid response for {command.id} (type: {command.command_type})')
            
#     # In case the end of the flight is coming near extend it
#     if flight.end is not None and (flight.end.timestamp() - datetime.now(timezone.utc).timestamp()) < FLIGHT_MINIMUM_HEAD_TIME.total_seconds():
#         flight.end = datetime.now(timezone.utc) + FLIGHT_DEFAULT_HEAD_TIME
#         flight.end = flight.end.replace(tzinfo=timezone.utc)
#         await create_or_update_flight(flight)

#     await insert_or_update_commands(commands, flight_id, False)

#     return 'success'

@flights_controller.get("/{flight_id}/commands")
async def get_commands(user:AuthOptional,flight_data:uuid.UUID,vessel_part:uuid.UUID=Query(), series_name:str=Query(),start:str=Query(),end:str=Query(),resolution:Optional[str]=Query(default=None)):
    if resolution:
        return await get_aggregated(flight_data, vessel_part, series_name, resolution, start, end, user)
    else:
        return await getRange(flight_data, vessel_part, start, end, user)

@command_controller.get("/get_aggregated_range/{flight_id}/{vessel_part}/{series_name}/{resolution}/{start}/{end}")
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

    values = await get_aggregated_flight_data_individual(flight_id, i, j, datetime.fromisoformat(start), datetime.fromisoformat(end), resolution, measurement_schema, 'commands') # type: ignore

    for v in values:
        v.part_id = uuid.UUID(flight.measured_part_ids[v.p_index])
        v.series_name = measurement_schema[v.m_index].name

    return values

@command_controller.get("/get_range/{flight_id}/{vessel_part}/{start}/{end}")
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
    
    values = await get_flight_data_in_range(series_identifier, datetime.fromisoformat(start), datetime.fromisoformat(end), 'commands')

    return values
