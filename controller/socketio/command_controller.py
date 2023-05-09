import asyncio
from typing import Coroutine, cast
from socketio import Server
from quart import current_app

from middleware.auth.requireAuth import socket_authenticated_only
from models.command import CommandSchema
from services.auth.jwt_user_info import get_user_info
from services.data_access.command import get_commands_new_signal, get_command_update_signal
from blinker import signal

new_command_event = 'command.new'
update_command_event = 'command.update'


def get_command_room_clients(flight_id: str):
    return f'command.client.flight_id[{flight_id}]'

def get_command_room_vessel(flight_id: str):
    return f'command.vessel.flight_id[{flight_id}]'

def make_on_new_command(sio: Server):

    def on_new_command(sender, **kw):

        flight_id = kw['flight_id']
        commands = kw['commands']
        from_client = kw['from_client']

        msg = {
            'commands': CommandSchema(many=True).dump_list(commands),
            'flight_id': flight_id
        }

        coroutine = sio.emit(new_command_event, msg, to=get_command_room_clients(flight_id))


        if from_client:
            coroutine_vessels = sio.emit(new_command_event, msg, to=get_command_room_vessel(flight_id))
            asyncio.get_event_loop().create_task(cast(Coroutine, coroutine_vessels))


        asyncio.get_event_loop().create_task(cast(Coroutine, coroutine))



    return on_new_command

def make_on_update_command(sio: Server):

    def on_update_command(sender, **kw):

        flight_id = kw['flight_id']
        commands = kw['commands']
        from_client = kw['from_client']

        msg = {
            'commands': CommandSchema().dump_list(commands),
            'flight_id': flight_id
        }

        if from_client:
            coroutine = sio.emit(update_command_event, msg, to=get_command_room_vessel(flight_id))
        else:
            coroutine = sio.emit(update_command_event, msg, to=get_command_room_clients(flight_id))

        asyncio.get_event_loop().create_task(cast(Coroutine, coroutine))

    return on_update_command

def init_command_controller(sio: Server):

    new_signal = get_commands_new_signal()
    update_signal = get_command_update_signal()

    # Connect the data access signal to emit flight data events
    new_signal.connect(make_on_new_command(sio), weak=False)
    update_signal.connect(make_on_update_command(sio), weak=False)

    @sio.on('command.subscribe')
    @socket_authenticated_only
    def subscribe(sid, flight_id):
        """ Join a room to receive all commands send for a specific flight"""

        user = get_user_info(sid)

        if user is None:
            return
        
        if 'Access.Vessel' in user.roles:
            sio.enter_room(sid, get_command_room_vessel(flight_id))
        else:
            sio.enter_room(sid, get_command_room_clients(flight_id))
            
        