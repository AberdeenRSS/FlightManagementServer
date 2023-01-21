from flask_socketio import SocketIO, join_room

from flask import current_app
from helper.model_helper import export_list

from middleware.auth.requireAuth import socket_authenticated_only
from services.data_access.command import get_command_new_signal
from blinker import signal

new_command_event = 'command.new'

def get_command_room(flight_id: str):
    return f'command.flight_id[{flight_id}]'

def get_on_new_command(socketio):

    def on_new_command(sender, **kw):

        flight_id = kw['flight_id']
        commands = kw['commands']

        socketio.emit(new_command_event, {'commands': export_list(commands)}, to=get_command_room)

    return on_new_command

def init_command_controller(socketio: SocketIO):

    s = get_command_new_signal()

    # Connect the data access signal to emit flight data events
    s.connect(get_on_new_command(socketio), weak=False)


    @socketio.on('command.subscribe')
    @socket_authenticated_only
    def subscribe(flight_id):
        """ Join a room to receive all flight data send in a specific flight"""
    
        join_room(get_command_room(flight_id))
        