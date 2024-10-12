from datetime import UTC, datetime, timezone
import json
from typing import Annotated, cast
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from ..middleware.auth.requireAuth import AuthOptional, user_optional, user_required, verify_role
from jsonschema import validate, ValidationError
from ..models.command import Command
from ..models.flight import FLIGHT_MINIMUM_HEAD_TIME, FLIGHT_DEFAULT_HEAD_TIME
from ..services.auth.jwt_user_info import UserInfo
from ..services.auth.permission_service import has_flight_permission
from ..services.data_access.command import get_commands_in_range, insert_commands, insert_or_update_commands
from ..services.data_access.flight import get_flight, create_or_update_flight
from ..services.data_access.vessel import get_vessel

command_controller = APIRouter(
    prefix="/command",
    tags=["command"],
    dependencies=[],
)

@command_controller.post("/dispatch/{flight_id}")
async def dispatch_commands(flight_id: UUID, commands: list[Command], user: Annotated[UserInfo, Depends(user_optional)]):
    """
    Dispatches a command to the vessel. Meant to be called from a ui/frontend or
    other type of client
    """

    if len(commands) < 1:
        raise HTTPException(400, 'Empty list of commands')

    for command in commands:

        command.create_time = cast(datetime, command.create_time.replace(tzinfo=timezone.utc))

        try:
            assert command.state == 'new'
            assert command.create_time is not None
            assert command.dispatch_time is None
            assert command.receive_time is None
            assert command.complete_time is None
        except AssertionError as e:
            raise HTTPException(400, f'Command {command.id} has wrong format: {e}')

    flight = await get_flight(flight_id)

    if flight is None:
        raise HTTPException(400, 'Flight does not exist')
    
    vessel = await get_vessel(flight.vessel_id)

    if vessel is None:
        raise HTTPException(400, 'Vessel does not exist')
    
    if not has_flight_permission(flight, vessel, 'write', user):
        raise HTTPException(403, 'You don\'t have write permission for this flight') 

    for command in commands:
        if command.command_type not in flight.available_commands:
            raise HTTPException(400, f'Command {command.command_type} does not exist')
                
        command_description = flight.available_commands[command.command_type]

        if not command_description.supported_on_vehicle_level and command.part_id is None:
            raise HTTPException(400, f'Command type {command.command_type} is not supported on vehicle level')

        if command.part_id is not None and command.part_id not in command_description.supporting_parts:
            raise HTTPException(400, f'Command type {command.command_type} not available for part {command.part_id}')

        if command_description.payload_schema is None:
            if command.command_payload is not None:
                raise HTTPException(400, f'Command {command.command_type} does not support a payload')
            continue

        if command.response is not None:
            raise HTTPException(401, f'A response can only be send by the vessel')

        try:
            validate(command.command_payload, command_description.payload_schema)
        except ValidationError:
            raise HTTPException(400, f'Invalid payload for {command.id} (type: {command.command_type})')
        
    # In case the end of the flight is coming near extend it
    # if flight.end is not None and (flight.end - datetime.now(UTC)) < FLIGHT_MINIMUM_HEAD_TIME:
    #     flight.end = datetime.now(UTC) + FLIGHT_DEFAULT_HEAD_TIME
    #     await create_or_update_flight(flight)

    await insert_commands(commands, flight_id, True)

    return 'success'

@command_controller.post("/confirm/{flight_id}")
async def confirm_command(flight_id: UUID, commands: list[Command], user: Annotated[UserInfo, Depends(user_required)]):
    """
    To be called by the vessel to confirm the the receipt or the
    processing of the command or that the vessel directly created a command
    """

    verify_role(user, 'vessel')

    flight = await get_flight(flight_id)

    if flight is None:
        raise HTTPException(404, 'Unknown flight')

    for command in commands:
        try:
            assert command.state != 'new'
            assert command.create_time
        except AssertionError:
            raise HTTPException(400, f'Command {command.id} has wrong format')

        if str(command.command_type) not in flight.available_commands:
            raise HTTPException(400, f'Command {command.command_type} does not exist')
        
        command_description = flight.available_commands[command.command_type]

        if not command_description.supported_on_vehicle_level and command.part_id is None:
            raise HTTPException(400, f'Command type {command.command_type} is not supported on vehicle level')

        if command.part_id is not None and command.part_id not in command_description.supporting_parts:
            raise HTTPException(400, f'Command type {command.command_type} not available for part {command.part_id}')
        
        if command.command_payload is not None and command_description.payload_schema is None:
            raise HTTPException(404, f'Command {command.command_type} does not support a payload')

        if command_description.payload_schema is not None:

            try:
                validate(command.command_payload, command_description.payload_schema)
            except ValidationError:
                raise HTTPException(404, f'Invalid payload for {command.id} (type: {command.command_type})')
            
        if command.response is not None and command_description.response_schema is None:
            raise HTTPException(400, f'Command {command.command_type} does not support a response')

        if command_description.response_schema is not None and command.command_payload is not None:

            try:
                validate(command.response, command_description.response_schema)
            except ValidationError:
                raise HTTPException(400, f'Invalid response for {command.id} (type: {command.command_type})')
            
    # In case the end of the flight is coming near extend it
    if flight.end is not None and (flight.end - datetime.now(UTC)) < FLIGHT_MINIMUM_HEAD_TIME:
        flight.end = datetime.now(UTC) + FLIGHT_DEFAULT_HEAD_TIME
        await create_or_update_flight(flight)

    await insert_or_update_commands(commands, flight_id, False)

    return 'success'

@command_controller.get("/get_range/{flight_id}/{start}/{end}/{command_type}/{vessel_part}")
async def get_range(flight_id: UUID, start: datetime, end: datetime, command_type: str, vessel_part: str, user: AuthOptional) -> list[Command]:
    """
    Gets all commands in the specified range
    """

    flight = await get_flight(flight_id)

    if flight is None:
        raise HTTPException(404, 'Flight does not exist')
    
    vessel = await get_vessel(flight.vessel_id)

    if vessel is None:
        raise HTTPException(404, 'Vessel does not exist')
    
    if not has_flight_permission(flight, vessel, 'write', user):
        raise HTTPException(403, 'You don\'t have write permission for this flight') 

    command_t = None
    part = None

    if command_type != 'all':
        command_t = command_type
    
    if vessel_part != 'all':
        part = UUID(vessel_part)

    values = await get_commands_in_range(flight_id, start, end, part, command_t)

    return values