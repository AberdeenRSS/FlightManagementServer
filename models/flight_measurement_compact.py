from dataclasses import dataclass, field
import datetime
from typing import Tuple, Union
from uuid import UUID

from marshmallow import fields

from helper.model_helper import make_safe_schema



@dataclass()
class FlightMeasurementCompact: 

    part_id: Union[UUID, None]

    field_names: list[str]

    measurements: list[Tuple[float, list[Union[str, int, float]]]] = field(default_factory=list)


class FlightMeasurementCompactSchema(make_safe_schema(FlightMeasurementCompact)):

    part_id = fields.UUID(allow_none=True)

    field_names = fields.List(fields.String)

    measurements = fields.List(fields.Tuple((fields.Float, fields.List(fields.Raw(allow_none=True)))))


@dataclass()
class FlightMeasurementCompactDB():

    part_id: Union[UUID, None]

    measurements: list[Tuple[float, list[Union[str, int, float, None]]]] = field(default_factory=list)

    _start_time: datetime.datetime = datetime.datetime.fromtimestamp(0)

    _end_time: datetime.datetime = datetime.datetime.fromtimestamp(0)

    measurements_aggregated: dict[str, tuple[Union[str, int, float, None]]] = field(default_factory=dict)

class FlightMeasurementCompactDBSchema(make_safe_schema(FlightMeasurementCompactDB)):

    _start_time = fields.AwareDateTime(default_timezone=datetime.timezone.utc)

    _end_time = fields.AwareDateTime(default_timezone=datetime.timezone.utc)

    part_id = fields.UUID(allow_none=True)

    measurements = fields.List(fields.Tuple((fields.Float, fields.List(fields.Raw(allow_none=True)))))

    measurements_aggregated = fields.Dict(fields.Str, fields.Tuple([fields.Raw(allow_none=True), fields.Raw(allow_none=True), fields.Raw(allow_none=True)]))

def to_compact_db(compact_measurement: FlightMeasurementCompact):

    avg_count = dict()
    avg_values = dict()
    min = dict()
    max = dict()

    for name in compact_measurement.field_names:

        avg_count[name] = 0
        avg_values[name] = 0
        min[name] = None
        max[name] = 0

    for timestamp, mm in compact_measurement.measurements:

        i = 0 
        for m in mm:
            
            if m is None or isinstance(m, str):
                i += 1
                continue

            field_name = compact_measurement.field_names[i]

            avg_values[field_name] += m
            avg_count[field_name] += 1

            if m > max[field_name]:
                max[field_name] = m

            if min[field_name] is None or m < min[field_name]:
                min[field_name] = m

            i += 1

    agg = dict[str, tuple]()

    for key, value in avg_values.items():

        avg = avg_values[key]/avg_count[key] if avg_count[key] > 0 else None

        agg[key] = (avg, min[key], max[key])

    first_timestamp = datetime.datetime.fromtimestamp(compact_measurement.measurements[0][0], tz=datetime.timezone.utc)
    last_timestamp = datetime.datetime.fromtimestamp(compact_measurement.measurements[-1][0], tz=datetime.timezone.utc)

    return FlightMeasurementCompactDB(
        _start_time = first_timestamp,
        _end_time = last_timestamp,
        part_id=compact_measurement.part_id,
        measurements=compact_measurement.measurements,
        measurements_aggregated=agg)
