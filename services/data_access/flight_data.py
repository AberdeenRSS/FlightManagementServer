from datetime import datetime
from typing import Literal, Sequence, Union, cast
from quart import current_app
from blinker import NamedSignal, Namespace, signal
from motor.core import AgnosticCollection, AgnosticDatabase

from models.flight_measurement import FlightMeasurement, FlightMeasurementDescriptor, FlightMeasurementSchema, FlightMeasurementDescriptorSchema, FlightMeasurementSeriesIdentifier, FlightMeasurementSeriesIdentifierSchema
from services.data_access.common.collection_managment import get_or_init_collection


#region Constants

epoch = datetime(1970, 1, 1)

resolutions: Sequence[Literal['decisecond', 'second', 'minute', 'hour', 'day', 'month']] = ['decisecond', 'second', 'minute', 'hour', 'day', 'month']

project_stage = { 
    '$project': {
        'dateParts': {
            '$dateToParts': {
                'date': '$_datetime'
            }
        }, 
        'measured_values': '$measured_values',
        '_datetime': '$_datetime'
    }
}

#endregion

#region Signals

NEW_FLIGHT_DATA = 'NEW_FLIGHT_DATA'

flight_data_signals = Namespace()
flight_data_signal = signal(f'{NEW_FLIGHT_DATA}')


# def get_flight_data_signal() -> NamedSignal:
#     global flight_data_signals
#     return 

#endregion

#region Helper

def get_date_grouping(resolution: str):
    date_id = {
        'year': '$dateParts.year', 
        'month': '$dateParts.month', 
        'day': '$dateParts.day', 
        'hour': '$dateParts.hour', 
        'minute': '$dateParts.minute', 
        'second': '$dateParts.second',
        'decisecond': { '$floor': { '$divide': ['$dateParts.millisecond', 100]}}
    }

    for r in resolutions:
        if r == resolution:
            return date_id
        date_id.popitem()
    return date_id

def get_averaging(schemas: list[FlightMeasurementDescriptor]):
    res = dict()

    for schema in schemas:
        field = f'$measured_values.{schema.name}'
        avg_field = f'avg_{schema.name}'
        min_field = f'min_{schema.name}'
        max_field = f'max_{schema.name}'
        res[avg_field] = {'$avg': field}
        res[min_field] = {'$min': field}
        res[max_field] = {'$max': field}

    return res

def get_aggregated_result_projection(schemas: list[FlightMeasurementDescriptor]):
    res = dict()

    for schema in schemas:
        avg_field = f'$avg_{schema.name}'
        min_field = f'$min_{schema.name}'
        max_field = f'$max_{schema.name}'

        res[schema.name] = { 'avg': avg_field, 'min': min_field, 'max': max_field }

    return res

# Removes all bson objects from the returned measurement
def debsonify_measurements(measurements: list[dict]):
    for r in measurements:
        r['_id'] = str(r['_id'])
        if '_datetime' in r:
            r['_datetime'] = cast(datetime, r['_datetime']).isoformat()

#endregion

#region Collection management

async def get_or_init_flight_data_collection(flight_id: str, vessel_part: str) -> AgnosticCollection:

    async def create_collection(db: AgnosticDatabase, n: str):
        return await db.create_collection(n, timeseries = {
            'timeField': '_datetime',
            'granularity': 'seconds'
        }) # type: ignore

    return await get_or_init_collection(f'flight_data_{flight_id.replace("-", "")}_part_{vessel_part.replace("-", "")}', create_collection)

#endregion

# Inserts new measured flight data
async def insert_flight_data(measurements: list[FlightMeasurement], flight_id: str, vessel_part: str):

    collection = await get_or_init_flight_data_collection(flight_id, vessel_part)

    # Convert into a datetime object, because mongodb
    # suddenly wants datetime objects instead of strings here
    measurements_raw = FlightMeasurementSchema().dump_list(measurements)

    for m in measurements_raw:
        m['_datetime'] = datetime.fromisoformat(m['_datetime'])

    res = await collection.insert_many(measurements_raw) # type: ignore

    s = cast(NamedSignal, signal(NEW_FLIGHT_DATA))

    s.send(current_app._get_current_object(), flight_id=flight_id, measurements = measurements, vessel_part = vessel_part) # type: ignore

async def get_flight_data_in_range(series_identifier: FlightMeasurementSeriesIdentifier, start: datetime, end: datetime) -> list[FlightMeasurement]:
    collection = await get_or_init_flight_data_collection(str(series_identifier._flight_id), str(series_identifier._vessel_part_id))

    # Get all measurements in the date range
    res = await collection.find({'_datetime': { '$gte': start, '$lt': end }  }).to_list(1000)

    debsonify_measurements(res)

    return FlightMeasurementSchema().load_list_safe(FlightMeasurement, res)

async def get_aggregated_flight_data(series_identifier: FlightMeasurementSeriesIdentifier, start: datetime, end: datetime, resolution: Literal['year', 'month', 'day', 'hour', 'minute', 'second', 'decisecond'], schemas: list[FlightMeasurementDescriptor] ):

    match_stage = {
        '$match': {
            '_datetime': { '$gte': start, '$lt': end }
        }
    }

    group_stage = {
        '$group': {
            '_id': {
                'date': get_date_grouping(resolution)
            },
            'start_date': {'$min': '$_datetime'},
            'end_date': {'$max': '$_datetime'}
        }
    }

    group_stage['$group'].update(get_averaging(schemas))

    project_aggregated_stage = {
        '$project': {
            'measured_values': { 
            },
            'start_date': '$start_date',
            'end_date': '$end_date'
        }
    }

    project_aggregated_stage['$project']['measured_values'].update(get_aggregated_result_projection(schemas))

    collection = await get_or_init_flight_data_collection(str(series_identifier._flight_id), str(series_identifier._vessel_part_id))

    res = await collection.aggregate([match_stage, project_stage, group_stage, project_aggregated_stage]).to_list(1000)

    # res = list(collection.aggregate(dummy))
    
    debsonify_measurements(res)

    return res