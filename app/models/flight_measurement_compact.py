import datetime
from typing import Tuple, Union
from uuid import UUID
from pydantic import BaseModel, Field

from app.helper.datetime_model import AwareDatetimeModel

class FlightMeasurementCompact(BaseModel): 

    part_id: Union[UUID, None]

    field_names: list[str]

    measurements: list[Tuple[float, list[Union[str, int, float, None]]]] = Field(default_factory=list)

MeasurementTypes = Union[str, int, float, None]

class FlightMeasurementCompactDB(AwareDatetimeModel):

    part_id: Union[UUID, None]

    measurements: list[Tuple[float, list[MeasurementTypes]]] = Field(default_factory=list)

    start_time: datetime.datetime = Field(alias='_start_time', alias_priority=1, default=datetime.datetime.fromtimestamp(0)) 

    end_time: datetime.datetime = Field(alias='_end_time', alias_priority=1, default=datetime.datetime.fromtimestamp(0)) 

    measurements_aggregated: dict[str, tuple[MeasurementTypes, MeasurementTypes, MeasurementTypes]] = Field(default_factory=dict)

def to_compact_db(compact_measurement: dict):

    avg_count = dict()
    avg_values = dict()
    min = dict()
    max = dict()

    for name in compact_measurement['field_names']:

        avg_count[name] = 0
        avg_values[name] = 0
        min[name] = None
        max[name] = 0

    for timestamp, mm in compact_measurement['measurements']:

        i = 0 
        for m in mm:
            
            if m is None or isinstance(m, str):
                i += 1
                continue

            field_name = compact_measurement['field_names'][i]

            avg_values[field_name] += m
            avg_count[field_name] += 1

            if m > max[field_name]:
                max[field_name] = m

            if min[field_name] is None or m < min[field_name]:
                min[field_name] = m

            i += 1

    agg = dict[str, tuple[MeasurementTypes, MeasurementTypes, MeasurementTypes]]()

    for key, value in avg_values.items():

        avg = avg_values[key]/avg_count[key] if avg_count[key] > 0 else None

        agg[key] = (avg, min[key], max[key])

    first_timestamp = datetime.datetime.fromtimestamp(compact_measurement['measurements'][0][0], tz=datetime.timezone.utc)
    last_timestamp = datetime.datetime.fromtimestamp(compact_measurement['measurements'][-1][0], tz=datetime.timezone.utc)

    return FlightMeasurementCompactDB(
        _start_time = first_timestamp,
        _end_time = last_timestamp,
        part_id=compact_measurement['part_id'],
        measurements=compact_measurement['measurements'],
        measurements_aggregated=agg)
