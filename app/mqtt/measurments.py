   
import asyncio
from datetime import datetime, timezone
import struct
import time
from typing import Any, Collection, Tuple

from app.helper.binary_format_encoder import decode_payload
from app.models.flight import FLIGHT_DEFAULT_HEAD_TIME, FLIGHT_MINIMUM_HEAD_TIME
from uuid import UUID

from app.models.flight_measurement import FlightMeasurementDB
from app.services.data_access.flight import create_or_update_flight, get_flight
from app.services.data_access.flight_data import insert_flight_data


CLEAR_INTERVAL = 0.5
FLOAT_SIZE = struct.calcsize('f')

class MeasurmentProcessor:

    def __init__(self, table: str, is_commands: bool) -> None:

        self.table = table
        self.is_commands = is_commands
        
        self.measurement_buffers = dict[str, dict[str, dict[str, list[bytes]]]]()
        self.last_cleared = dict[str, float]()


    def process_measurements(self, flight_uuid: str, part: str, measurement_index: str, paylaod: bytes):

        if flight_uuid not in self.measurement_buffers:
            self.measurement_buffers[flight_uuid] = dict()
        
        vessel_buffer = self.measurement_buffers[flight_uuid]

        if part not in vessel_buffer:
            vessel_buffer[part] = dict()

        part_buffer = vessel_buffer[part]

        if measurement_index not in part_buffer:
            part_buffer[measurement_index] = list()

        part_buffer[measurement_index].append(paylaod)

        if flight_uuid not in self.last_cleared:
            self.last_cleared[flight_uuid] = time.time()
            return
        
        time_since_last_cleared = (time.time() - self.last_cleared[flight_uuid])
        
        if time_since_last_cleared  < CLEAR_INTERVAL:
            return

        self.measurement_buffers[flight_uuid] = dict() # swap buffer first for subsequent measuremetns
        self.last_cleared[flight_uuid] = time.time()

        asyncio.get_event_loop().create_task(self.clear_measurement_buffer(flight_uuid, vessel_buffer))

        # asyncio.create_task()
        
    async def clear_measurement_buffer(self, flight_uuid: str, vessel_buffer: dict[str, dict[str, list[bytes]]]):


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
            descriptors = flight.available_commands[part_id] if self.is_commands else flight.measured_parts[part_id] 

            for measurment_index, measurements in part_buffer.items():

                descriptor = descriptors[int(measurment_index)].payload_schema if self.is_commands else descriptors[int(measurment_index)].type # type: ignore

                mesaurement_tuples = list[Tuple]()

                start = 1e22
                end = 0

                for m in measurements:

                    time, res = decode_payload(descriptor, m)  # type: ignore

                    mesaurement_tuples.append((time, res))

                    if time < start:
                        start = time

                    if time > end:
                        end = time

                agg = aggregate_measurements(descriptor, mesaurement_tuples) # type: ignore

                db_object = FlightMeasurementDB(
                    p_index=int(part_index),
                    m_index=int(measurment_index),
                    measurements=mesaurement_tuples,
                    _start_time=datetime.fromtimestamp(start, tz=timezone.utc),
                    _end_time=datetime.fromtimestamp(end, tz=timezone.utc),
                    min = agg[0],
                    avg = agg[1],
                    max = agg[2],
                )
                db_objects.append(db_object)

        await insert_flight_data(db_objects, UUID(flight_uuid), self.table)

def aggregate_measurements(descriptor: str | list[tuple[str, str]], tuples: list[tuple[float, Any]]):

    if not isinstance(descriptor, str):
        return (None, None, None)

    if descriptor.startswith('!'):
        descriptor = descriptor.replace('!', '')

    # Default case: 
    if len(descriptor) > 1:
        return (None, None, None)
    
    is_bool = descriptor == '?'

    min = 1e100
    max = 0
    avg = 0

    for time, value in tuples:
        v = (1 if value else 0) if is_bool else value
        if v < min:
            min = v
        if v > max:
            max = v
        avg += v

    return (min, avg/len(tuples), max)

def can_aggregate(descriptor: str):

    if descriptor.startswith('!'):
        descriptor = descriptor.replace('!', '')

    return len(descriptor) > 0