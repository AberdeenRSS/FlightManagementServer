from flask_socketio import SocketIO, join_room

from flask import current_app

from middleware.auth.requireAuth import socket_authenticated_only
from models.command import CommandSchema
from services.data_access.command import get_commands_new_signal, get_command_update_signal
from blinker import signal

new_command_event = 'command.new'
update_command_event = 'command.update'


def get_command_room(flight_id: str):
    return f'command.flight_id[{flight_id}]'

def make_on_new_command(socketio):

    def on_new_command(sender, **kw):

        flight_id = kw['flight_id']
        commands = kw['commands']

        msg = {
            'commands': CommandSchema(many=True).dump_list(commands),
            'flight_id': flight_id
        }

        socketio.emit(new_command_event, msg, to=get_command_room(flight_id))

    return on_new_command

def make_on_update_command(socketio):

    def on_update_command(sender, **kw):

        flight_id = kw['flight_id']
        commands = kw['command']

        msg = {
            'command': CommandSchema().dump(commands),
            'flight_id': flight_id
        }

        socketio.emit(update_command_event, msg, to=get_command_room(flight_id))

    return on_update_command

def init_command_controller(socketio: SocketIO):

    new_signal = get_commands_new_signal()
    update_signal = get_command_update_signal()

    # Connect the data access signal to emit flight data events
    new_signal.connect(make_on_new_command(socketio), weak=False)
    update_signal.connect(make_on_update_command(socketio), weak=False)

    @socketio.on('command.subscribe')
    @socket_authenticated_only
    def subscribe(flight_id):
        """ Join a room to receive all flight data send in a specific flight"""
    
        join_room(get_command_room(flight_id))
        