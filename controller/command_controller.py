from datetime import datetime, timezone
import json
from typing import cast
from quart import Blueprint
from quart import request, flash, g, jsonify
from middleware.auth.requireAuth import auth_required
from uuid import uuid4

from jsonschema import validate, ValidationError

from models.command import CommandSchema, Command
from models.flight import FLIGHT_MINIMUM_HEAD_TIME, FLIGHT_DEFAULT_HEAD_TIME
from services.auth.jwt_user_info import User, get_user_info
from services.data_access.command import get_commands_in_range, insert_commands, insert_or_update_commands
from services.data_access.flight import get_flight, create_or_update_flight
from services.data_access.vessel import get_vessel


command_controller = Blueprint('command', __name__, url_prefix='/command')

@command_controller.route("/dispatch/<flight_id>", methods = ['POST'])
@auth_required
async def dispatch_commands(flight_id: str):
    """
    Dispatches a command to the vessel. Meant to be called from a ui/frontend or
    other type of client
    ---
    parameters:
      - name: flight_id
        required: true
        in: path
        type: string
        description: The id of the flight the command is dispatched for
      - name: body
        required: true
        in: body
        schema:
            type: array
            items:
                $ref: "#/definitions/Command"
        description: A list of measurements that is being reported
    responses:
        200:
            description: Success
            schema:
                type: string
        400:
            description: The command data is formatted wrong or the given command is not available for the vessel
        401:
            description: The user issuing the command does not have the required authorization to do so 
        404:
            description: The flight does not exist
    """

    parsed_commands = await request.get_json()

    if not isinstance(parsed_commands, list):
        return f'Invalid json, commands have to be send as an array', 400

    commands = CommandSchema().load_list_safe(Command, parsed_commands)

    if len(commands) < 1:
        return f'Empty list', 400

    user_info = cast(User, get_user_info())

    for command in commands:
        try:
            assert command.state == 'new'
            assert command.create_time
            assert cast(datetime, command.create_time.replace(tzinfo=timezone.utc)) < datetime.utcnow().replace(tzinfo=timezone.utc)
            assert command.dispatch_time == None
            assert command.receive_time == None
            assert command.complete_time == None
        except AssertionError:
            return f'Command {command._id} has wrong format', 400

    flight = await get_flight(flight_id)

    if flight is None:
        return 'Unknown flight', 404

    for command in commands:
        if command._command_type not in flight.available_commands:
            return f'Command {command._command_type} does not exist', 400
        
        command_description = flight.available_commands[command._command_type]

        if not command_description.supported_on_vehicle_level and command._part_id is None:
            return f'Command type {command._command_type} is not supported on vehicle level'

        if command._part_id is not None and command._part_id not in command_description.supporting_parts:
            return f'Command type {command._command_type} not available for part {command._part_id}', 400

        if command_description.payload_schema is None:
            if command.command_payload is not None:
                return f'Command {command._command_type} does not support a payload', 400
            continue

        if command.response is not None:
            return f'A response can only be send by the vessel', 401

        try:
            validate(command.command_payload, command_description.payload_schema)
        except ValidationError:
            return f'Invalid payload for {command._id} (type: {command._command_type})', 400
        
    # In case the end of the flight is coming near extend it
    if flight.end is not None and (flight.end - datetime.now(timezone.utc)) < FLIGHT_MINIMUM_HEAD_TIME:
        flight.end = datetime.utcnow() + FLIGHT_DEFAULT_HEAD_TIME
        await create_or_update_flight(flight)

    await insert_commands(commands, flight_id, True)

    return '', 200

@command_controller.route("/confirm/<flight_id>", methods = ['POST'])
@auth_required
async def confirm_command(flight_id: str):
    """
    To be called by the vessel to confirm the the receipt or the
    processing of the command or that the vessel directly created a command
    ---
    parameters:
      - name: flight_id
        required: true
        in: path
        type: string
        description: The id of the flight the command is for
      - name: body
        required: true
        in: body
        schema:
            type: array
            items:
                $ref: "#/definitions/Command"
        description: The updated command
    responses:
        200:
            description: Success
            schema:
                type: string
        400:
            description: The command data is formatted wrong or the given command is not available for the vessel
        401:
            description: The user confirming the command is not the vessel
        404:
            description: The flight does not exist
    """

    parsed_command = await request.get_json()

    commands = CommandSchema().load_list_safe(Command, json.loads(parsed_command))

    user_info = cast(User, get_user_info())

    flight = await get_flight(flight_id)

    if flight is None:
        return 'Unknown flight', 404

    for command in commands:
        try:
            assert command.state != 'new'
            assert command.create_time
        except AssertionError:
            return f'Command {command._id} has wrong format', 400

        if str(command._command_type) not in flight.available_commands:
            return f'Command {command._command_type} does not exist', 400
        
        command_description = flight.available_commands[command._command_type]

        if not command_description.supported_on_vehicle_level and command._part_id is None:
            return f'Command type {command._command_type} is not supported on vehicle level'

        if command._part_id is not None and command._part_id not in command_description.supporting_parts:
            return f'Command type {command._command_type} not available for part {command._part_id}', 400
        
        if command.command_payload is not None and command_description.payload_schema is None:
            return f'Command {command._command_type} does not support a payload', 400

        if command_description.payload_schema is not None:

            try:
                validate(command.command_payload, command_description.payload_schema)
            except ValidationError:
                return f'Invalid payload for {command._id} (type: {command._command_type})', 400
            
        if command.response is not None and command_description.response_schema is None:
            return f'Command {command._command_type} does not support a response', 400

        if command_description.response_schema is not None and command.command_payload is not None:

            try:
                validate(command.response, command_description.response_schema)
            except ValidationError:
                return f'Invalid response for {command._id} (type: {command._command_type})', 400
            
    # In case the end of the flight is coming near extend it
    if flight.end is not None and (flight.end - datetime.now(timezone.utc)) < FLIGHT_MINIMUM_HEAD_TIME:
        flight.end = datetime.utcnow() + FLIGHT_DEFAULT_HEAD_TIME
        await create_or_update_flight(flight)

    await insert_or_update_commands(commands, flight_id, False)

    return '', 200

@command_controller.route("/get_range/<flight_id>/<start>/<end>/<command_type>/<vessel_part>", methods = ['GET'])
@auth_required
async def get_range(flight_id: str, start: str, end: str, command_type: str, vessel_part: str,):
    """
    Gets all commands in the specified range
    ---
    parameters:
      - name: flight_id
        required: true
        in: path
        type: string
        description: The id of the flight the measurements are requested for
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
      - name: command_type
        required: true
        in: path
        type: string
        description: The command type to get (Can also be "all" to get all commands)
      - name: vessel_part
        required: true
        in: path
        type: string
        description: The vessel part of the command (Can also be "all" to get commands for all parts)
    responses:
      200:
        description: The commands in the requested range
        schema:
          type: array
          items:
            $ref: "#/definitions/Command"
    """

    if start.endswith('Z'):
        start = start[:-1]
    if end.endswith('Z'):
        end = end[:-1]

    command_t = None
    part = None

    if command_type != 'all':
        command_t = command_type
    
    if vessel_part != 'all':
        part = vessel_part

    values = await get_commands_in_range(flight_id, datetime.fromisoformat(start), datetime.fromisoformat(end), part, command_t)

    return jsonify(CommandSchema().dump_list(values))