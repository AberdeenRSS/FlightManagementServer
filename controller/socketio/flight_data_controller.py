import asyncio
from typing import Coroutine, cast
from socketio import Server

from quart import current_app

from middleware.auth.requireAuth import socket_authenticated_only
from models.flight_measurement import FlightMeasurementSchema
from services.data_access.flight_data import flight_data_signal, NEW_FLIGHT_DATA
from blinker import NamedSignal, signal

new_flight_data_event = 'flight_data.new'

def get_flight_data_room(flight_id: str):
    return f'flight_data.flight_id[{flight_id}]'

def get_on_new_flight_data(sio: Server):

    def on_new_flight_data(sender, **kw):

        flight_id       = kw['flight_id']
        vessel_part     = kw['vessel_part']
        measurements    = kw['measurements']

        msg = {
            'measurements': FlightMeasurementSchema().dump_list(measurements),
            'flight_id': flight_id
        }

        coroutine = sio.emit(new_flight_data_event, msg, to=get_flight_data_room(flight_id))

        asyncio.get_event_loop().create_task(cast(Coroutine, coroutine))

        return

    return on_new_flight_data

def init_flight_data_controller(sio: Server):

    s = cast(NamedSignal, signal(NEW_FLIGHT_DATA))

    # Connect the data access signal to emit flight data events
    s.connect(get_on_new_flight_data(sio), weak=False)


    @sio.on('flight_data.subscribe')
    @socket_authenticated_only
    def subscribe(sid, flight_id):
        """ Join a room to receive all flight data send in a specific flight"""
    
        sio.enter_room(sid, get_flight_data_room(flight_id))
        