import asyncio
from logging import Logger
from typing import Coroutine, cast
from socketio import Server
from blinker import Signal

from app.middleware.auth.requireAuth import socket_authenticated_only, socket_use_auth
from app.models.flight import Flight
from app.services.data_access.flight import get_flight_new_signal, get_flight_update_signal

flight_new_event = 'flights.new'
flight_update_event = 'flights.update'

def get_flight_room():
    return f'flights'

def make_on_new_flight(sio: Server):

    def on_new_flight(sender, **kw):

        flight: Flight = kw['flight']
        coroutine = sio.emit(flight_new_event, flight.model_dump(by_alias=True), to=get_flight_room())

        asyncio.get_event_loop().create_task(cast(Coroutine, coroutine))

    return on_new_flight

def make_on_update_flight(sio: Server):

    def on_update_flight(sender, **kw):

        flight: Flight = kw['flight']

        coroutine = sio.emit(flight_update_event, flight.model_dump(by_alias=True), to=get_flight_room())

        asyncio.get_event_loop().create_task(cast(Coroutine, coroutine))

    return on_update_flight

def init_flight_controller(sio: Server, logger: Logger | None):

    new_signal = get_flight_new_signal()
    update_signal = get_flight_update_signal()

    # Connect the data access signal to emit flight data events
    new_signal.connect(make_on_new_flight(sio), weak=False)
    update_signal.connect(make_on_update_flight(sio), weak=False)

    @sio.on('flights.subscribe')
    @socket_use_auth(sio)
    async def subscribe(sid):
        """ Join a room to receive updates if flights are created/modified"""
    
        await sio.enter_room(sid, get_flight_room()) # type: ignore
        