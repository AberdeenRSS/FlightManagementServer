   
import asyncio
from datetime import datetime, timezone
import struct
import time
from typing import Tuple

from app.models.flight import FLIGHT_DEFAULT_HEAD_TIME, FLIGHT_MINIMUM_HEAD_TIME
from uuid import UUID

from app.models.flight_measurement_individual_compact import FlightMeasurementIndividualCompactDB
from app.services.data_access.flight import create_or_update_flight, get_flight
from app.services.data_access.flight_data_compact_individual import insert_flight_data

measurement_buffers = dict[str, dict[str, dict[str, list[bytes]]]]()
last_cleared = dict[str, float]()

CLEAR_INTERVAL = 0.5
FLOAT_SIZE = struct.calcsize('f')

def process_measurements(flight_uuid: str, part: str, measurement_index: str, paylaod: bytes):


    if flight_uuid not in measurement_buffers:
        measurement_buffers[flight_uuid] = dict()
    
    vessel_buffer = measurement_buffers[flight_uuid]

    if part not in vessel_buffer:
        vessel_buffer[part] = dict()

    part_buffer = vessel_buffer[part]

    if measurement_index not in part_buffer:
        part_buffer[measurement_index] = list()

    part_buffer[measurement_index].append(paylaod)

    if flight_uuid not in last_cleared:
        last_cleared[flight_uuid] = time.time()
        return
    
    if (time.time() - last_cleared[flight_uuid]) < CLEAR_INTERVAL:
        return

    measurement_buffers[flight_uuid] = dict() # swap buffer first for subsequent measuremetns
    last_cleared[flight_uuid] = time.time()

    asyncio.get_event_loop().create_task(clear_measurement_buffer(flight_uuid, vessel_buffer))

    # asyncio.create_task()
    
async def clear_measurement_buffer(flight_uuid: str, vessel_buffer: dict[str, dict[str, list[bytes]]]):


    flight = await get_flight(UUID(flight_uuid))

    if flight is None:
        print(f'invalid flight: {flight_uuid}')
        return
    
    # In case the end of the flight is coming near extend it
    if flight.end is not None and (flight.end.timestamp() - datetime.now(timezone.utc).timestamp()) < FLIGHT_MINIMUM_HEAD_TIME.total_seconds():
        flight.end = datetime.now(timezone.utc) + FLIGHT_DEFAULT_HEAD_TIME
        flight.end = flight.end.replace(tzinfo=timezone.utc)
        await create_or_update_flight(flight)
    
    # parsed = FlightMeasurementCompactSchema().load_list_safe(FlightMeasurementCompact, parsed_data)

    # after_parse_time = time.time()

    db_objects = list()

    for part_index, part_buffer in vessel_buffer.items():

        part_id = flight.measured_part_ids[int(part_index)]
        descriptors = flight.measured_parts[part_id]


        for measurment_index, measurements in part_buffer.items():

            descriptor = descriptors[int(measurment_index)]

            mesaurement_tuples = list[Tuple]()

            start = 1e22
            end = 0

            if descriptor.type == '[str]':
                for m in measurements:
                    time, = struct.unpack('!d', m[:FLOAT_SIZE])
                    msg = m[FLOAT_SIZE:].decode('utf-8')
                    mesaurement_tuples.append((time, msg))
                    if time < start:
                        start = time
                    if time > end:
                        end = time
            else:
                for m in measurements:
                    items = struct.unpack(f'!d{descriptor.type}', m)
                    time = items[0]
                    mesaurement_tuples.append(items)
                    if time < start:
                        start = time
                    if time > end:
                        end = time

            db_object = FlightMeasurementIndividualCompactDB(p_index=int(part_index), m_index=int(measurment_index), measurements=mesaurement_tuples, _start_time=datetime.fromtimestamp(start), _end_time=datetime.fromtimestamp(end))
            db_objects.append(db_object)

    await insert_flight_data(db_objects, UUID(flight_uuid))