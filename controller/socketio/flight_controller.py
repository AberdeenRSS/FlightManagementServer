import asyncio
from logging import Logger
from typing import Coroutine, cast
from quart import current_app
from socketio import Server
from models.flight import FlightSchema
from middleware.auth.requireAuth import socket_authenticated_only
from blinker import signal

from services.data_access.flight import get_flight_new_signal, get_flight_update_signal

flight_new_event = 'flights.new'
flight_update_event = 'flights.update'

def get_flight_room():
    return f'flights'

def make_on_new_command(sio: Server):

    def on_new_command(sender, **kw):

        flight = kw['flight']
        coroutine = sio.emit(flight_new_event, FlightSchema().dump(flight), to=get_flight_room())

        asyncio.get_event_loop().create_task(cast(Coroutine, coroutine))


    return on_new_command

def make_on_update_command(sio: Server):

    def on_update_command(sender, **kw):

        flight = kw['flight']
        coroutine = sio.emit(flight_update_event, FlightSchema().dump(flight), to=get_flight_room())

        asyncio.get_event_loop().create_task(cast(Coroutine, coroutine))

    return on_update_command

def init_flight_controller(sio: Server, logger: Logger):

    new_signal = get_flight_new_signal()
    update_signal = get_flight_update_signal()

    # Connect the data access signal to emit flight data events
    new_signal.connect(make_on_new_command(sio), weak=False)
    update_signal.connect(make_on_update_command(sio), weak=False)

    @sio.on('flights.subscribe')
    @socket_authenticated_only
    def subscribe(sid):
        """ Join a room to receive all flight data send in a specific flight"""
    
        sio.enter_room(sid, get_flight_room())
        