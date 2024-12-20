import asyncio
from logging import Logger
from typing import Coroutine, cast
from uuid import UUID
from socketio import Server
from blinker import signal

from app.middleware.auth.requireAuth import role_required_socket, socket_authenticated_only, socket_use_auth
from app.models.command import Command
from app.services.auth.jwt_user_info import get_socket_user_info, require_socket_user_info
from app.services.auth.permission_service import has_flight_permission
from app.services.data_access.command import get_commands_new_signal, get_command_update_signal
from app.services.data_access.flight import get_flight
from app.services.data_access.vessel import get_vessel

new_command_event = 'command.new'
update_command_event = 'command.update'


def get_command_room_clients(flight_id: str):
    return f'command.client.flight_id[{flight_id}]'

def get_command_room_vessel(flight_id: str):
    return f'command.vessel.flight_id[{flight_id}]'

def make_on_new_command(sio: Server):

    def on_new_command(sender, **kw):
        
        try:

            flight_id = kw['flight_id']
            commands: list[Command] = kw['commands']
            from_client = kw['from_client']

            msg = {
                'commands': [c.model_dump(by_alias=True) for c in commands],
                'flight_id': flight_id
            }

            coroutine = sio.emit(new_command_event, msg, to=get_command_room_clients(flight_id))


            if from_client:
                coroutine_vessels = sio.emit(new_command_event, msg, to=get_command_room_vessel(flight_id))
                asyncio.get_event_loop().create_task(cast(Coroutine, coroutine_vessels))


            asyncio.get_event_loop().create_task(cast(Coroutine, coroutine))

        except Exception as e:

            # current_app.logger.error(f'Error sending command {e}')
            pass


    return on_new_command

def make_on_update_command(sio: Server):

    def on_update_command(sender, **kw):

        try:

            flight_id = kw['flight_id']
            commands: list[Command] = kw['commands']
            from_client = kw['from_client']

            msg = {
                'commands': [c.model_dump(by_alias=True) for c in commands],
                'flight_id': flight_id
            }

            room = get_command_room_vessel(flight_id) if from_client else get_command_room_clients(flight_id)
            coroutine = sio.emit(update_command_event, msg, to=room)

            asyncio.get_event_loop().create_task(cast(Coroutine, coroutine))
        except Exception as e:

            # current_app.logger.error(f'Error sending command: {e}')
            pass

    return on_update_command

def init_command_controller(sio: Server, logger: Logger | None):

    new_signal = get_commands_new_signal()
    update_signal = get_command_update_signal()

    # Connect the data access signal to emit flight data events
    new_signal.connect(make_on_new_command(sio), weak=False)
    update_signal.connect(make_on_update_command(sio), weak=False)

    @sio.on('command.subscribe_as_client')
    @socket_use_auth(sio)
    async def subscribe_as_client(sid, flight_id):
        """ Join a room to receive all commands send for a specific flight"""

        user = require_socket_user_info(sid)

        flight = await get_flight(UUID(flight_id))

        if flight is None:
            return 'Flight does not exist', 404
    
        vessel = await get_vessel(flight.vessel_id)

        if vessel is None:
            return 'Vessel does not exist', 404
        
        if not has_flight_permission(flight, vessel, 'read', user):
            return 'You don\'t have the required permission to access the flight', 403
        
        room = get_command_room_clients(flight_id)

        await sio.enter_room(sid, room) # type: ignore

    @sio.on('command.subscribe_as_vessel')
    @socket_authenticated_only(sio)
    @role_required_socket('vessel')
    async def subscribe_as_vessel(sid, flight_id):
        """ Join a room to receive all commands send for a specific flight"""

        # user = get_user_info(sid)

        # if user is None:
        #     return
        
        room = get_command_room_vessel(flight_id)

        await sio.enter_room(sid, room)

            
        