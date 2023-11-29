import asyncio
from logging import Logger
from typing import Coroutine, cast
from socketio import Server

from quart import current_app

from middleware.auth.requireAuth import socket_authenticated_only, socket_use_auth
from models.flight_measurement import FlightMeasurementSchema
from models.flight_measurement_compact import FlightMeasurementCompactDB, FlightMeasurementCompactDBSchema
from services.auth.permission_service import has_flight_permission
from services.data_access.flight import get_flight
from services.data_access.flight_data_compact import NEW_FLIGHT_DATA_COMPACT
from blinker import NamedSignal, signal

from services.data_access.vessel import get_vessel

new_flight_data_event = 'flight_data.new'

def get_flight_data_room(flight_id: str):
    return f'flight_data.flight_id[{flight_id}]'

def get_on_new_flight_data(sio: Server):

    def on_new_flight_data(sender, **kw):

        try:

            flight_id       = kw['flight_id']
            measurements    = kw['measurements']

            # Delete most granular data to save bandwidth
            for m in measurements:
                del m.measurements

            msg = {
                'measurements': FlightMeasurementCompactDBSchema().dump_list(measurements),
                'flight_id': flight_id
            }

            coroutine = sio.emit(new_flight_data_event, msg, to=get_flight_data_room(flight_id))

            asyncio.get_event_loop().create_task(cast(Coroutine, coroutine))
        except Exception as e:

            current_app.logger.error(f'Error sending realtime flight data: {e}')

        return

    return on_new_flight_data

def init_flight_data_controller(sio: Server, logger: Logger):

    s = cast(NamedSignal, signal(NEW_FLIGHT_DATA_COMPACT))

    # Connect the data access signal to emit flight data events
    s.connect(get_on_new_flight_data(sio), weak=False)


    @sio.on('flight_data.subscribe')
    @socket_use_auth
    async def subscribe(sid, flight_id):
        """ Join a room to receive all flight data send in a specific flight"""

        flight = await get_flight(flight_id)

        if flight is None:
            return 'Flight does not exist', 404
    
        vessel = await get_vessel(str(flight._vessel_id))

        if vessel is None:
            return 'Vessel does not exist', 404
        
        if not has_flight_permission(flight, vessel, 'read'):
            return 'You don\'t have the required permission to access the flight', 403
    
        sio.enter_room(sid, get_flight_data_room(flight_id))
        