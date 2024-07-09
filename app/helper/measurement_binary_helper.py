import struct
from typing import Tuple, Union
from uuid import UUID
from typing_extensions import Buffer
from app.models.flight import Flight
from app.models.flight_measurement import FlightMeasurementDescriptor
from io import BufferedIOBase, BytesIO

from app.models.flight_measurement_compact import FlightMeasurementCompact, FlightMeasurementCompactDB

CHAR_SIZE = struct.calcsize('!B')
SHORT_SIZE = struct.calcsize('!H')

# Gets the struct descriptor for the measurement of the part see https://docs.python.org/3.5/library/struct.html
def get_struct_format_for_part(descriptiors: list[FlightMeasurementDescriptor]) -> str:

    # First value is always the dattime of the measurement as a float
    res = '!d'

    for descriptor in descriptiors:
            res += descriptor.type

    return res


def parse_binary_measurements(m: BytesIO, flight: Flight) -> list[FlightMeasurementCompact]:

    measurements = list[FlightMeasurementCompact]()

    while True:

        values = list()

        index_bytes = m.read1(CHAR_SIZE) 

        count_bytes = m.read1(SHORT_SIZE)

        if not index_bytes:
            break

        part_index = struct.unpack_from('!B', index_bytes)[0]
        measurement_count = struct.unpack_from('!H', count_bytes)[0]

        try:
            part_id = flight.measured_part_ids[part_index] 
        except:
            pass
        part = flight.measured_parts[part_id]

        struct_descriptor = get_struct_format_for_part(part)

        j = 0

        size = struct.calcsize(struct_descriptor)

        while j < measurement_count: 

            value_bytes = m.read1(size)

            unpacked_values = struct.unpack_from(struct_descriptor, value_bytes)

            values.append((unpacked_values[0], unpacked_values[1:len(part)+1]))

            j += 1

        measurements.append(FlightMeasurementCompact(part_id = UUID(part_id), field_names = [x.name for x in part], measurements = values))
    
    return measurements