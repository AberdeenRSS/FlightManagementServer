from flask_socketio import SocketIO, join_room

from flask import current_app
from models.flight import FlightSchema
from middleware.auth.requireAuth import socket_authenticated_only
from blinker import signal

from services.data_access.flight import get_flight_new_signal, get_flight_update_signal

flight_new_event = 'flights.new'
flight_update_event = 'flights.update'

def get_flight_room():
    return f'flights'

def make_on_new_command(socketio):

    def on_new_command(sender, **kw):

        flight = kw['flight']
        socketio.emit(flight_new_event, FlightSchema().dump(flight), to=get_flight_room())

    return on_new_command

def make_on_update_command(socketio):

    def on_update_command(sender, **kw):

        flight = kw['flight']
        socketio.emit(flight_update_event, FlightSchema().dump(flight), to=get_flight_room())

    return on_update_command

def init_flight_controller(socketio: SocketIO):

    new_signal = get_flight_new_signal()
    update_signal = get_flight_update_signal()

    # Connect the data access signal to emit flight data events
    new_signal.connect(make_on_new_command(socketio), weak=False)
    update_signal.connect(make_on_update_command(socketio), weak=False)

    @socketio.on('flights.subscribe')
    @socket_authenticated_only
    def subscribe():
        """ Join a room to receive all flight data send in a specific flight"""
    
        join_room(get_flight_room())
        