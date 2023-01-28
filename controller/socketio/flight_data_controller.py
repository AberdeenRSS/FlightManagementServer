from flask_socketio import SocketIO, join_room

from flask import current_app

from middleware.auth.requireAuth import socket_authenticated_only
from models.flight_measurement import FlightMeasurementSchema
from services.data_access.flight_data import flight_data_signal, NEW_FLIGHT_DATA
from blinker import signal

new_flight_data_event = 'flight_data.new'

def get_flight_data_room(flight_id: str):
    return f'flight_data.flight_id[{flight_id}]'

def get_on_new_flight_data(socketio):

    def on_new_flight_data(sender, **kw):

        flight_id       = kw['flight_id']
        vessel_part     = kw['vessel_part']
        measurements    = kw['measurements']

        msg = {
            'measurements': FlightMeasurementSchema().dump_list(measurements),
            'flight_id': flight_id,
            'vessel_part': vessel_part
        }

        socketio.emit(new_flight_data_event, msg, to=get_flight_data_room(flight_id))

    return on_new_flight_data

def init_flight_data_controller(socketio: SocketIO):

    s = signal(NEW_FLIGHT_DATA)

    # Connect the data access signal to emit flight data events
    s.connect(get_on_new_flight_data(socketio), weak=False)


    @socketio.on('flight_data.subscribe')
    @socket_authenticated_only
    def subscribe(flight_id):
        """ Join a room to receive all flight data send in a specific flight"""
    
        join_room(get_flight_data_room(flight_id))
        