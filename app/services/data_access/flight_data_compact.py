from datetime import datetime
from typing import Literal, Sequence, Union, cast
from uuid import UUID
from blinker import NamedSignal, Namespace, signal
from motor.core import AgnosticCollection, AgnosticDatabase
from pymongo import ASCENDING, DESCENDING

from app.models.flight_measurement import FlightMeasurement, FlightMeasurementDescriptor, FlightMeasurementSeriesIdentifier
from app.models.flight_measurement_compact import FlightMeasurementCompactDB
from app.services.data_access.common.collection_managment import get_or_init_collection
from time import time

#region Constants

epoch = datetime(1970, 1, 1)

resolutions: Sequence[Literal['decisecond', 'second', 'minute', 'hour', 'day', 'month']] = ['decisecond', 'second', 'minute', 'hour', 'day', 'month']

project_stage = { 
    '$project': {
        'dateParts': {
            '$dateToParts': {
                'date': '$_start_time'
            }
        }, 
        'measurements_aggregated': '$measurements_aggregated',
        '_start_time': '$_start_time'
    }
}

#endregion

#region Signals

NEW_FLIGHT_DATA_COMPACT = 'NEW_FLIGHT_DATA_COMPACT'

flight_data_signals = Namespace()
flight_data_signal = signal(f'{NEW_FLIGHT_DATA_COMPACT}')


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
        field = f'$measurements_aggregated.{schema.name}'

        res_field_avg = f'{schema.name}_avg'
        res_field_min = f'{schema.name}_min'
        res_field_max = f'{schema.name}_max'

        res[res_field_avg] = {"$avg": { '$arrayElemAt': [field, 0]}}
        res[res_field_min] = {"$min": { '$arrayElemAt': [field, 1]}}
        res[res_field_max] = {"$max": { '$arrayElemAt': [field, 2]}}

    return res

def get_aggregated_result_projection(schemas: list[FlightMeasurementDescriptor]):
    res = dict()

    for schema in schemas:

        res_field_avg = f'${schema.name}_avg'
        res_field_min = f'${schema.name}_min'
        res_field_max = f'${schema.name}_max'

        res[schema.name] = [
            res_field_avg,
            res_field_min,
            res_field_max
            # {'$getField': res_field_avg},
            # {'$getField': res_field_min},
            # {'$getField': res_field_max}
        ]

    return res

# Removes all bson objects from the returned measurement
def debsonify_measurements(measurements: list[dict]):
    for r in measurements:
        r['_id'] = str(r['_id'])
        if '_datetime' in r:
            r['_datetime'] = cast(datetime, r['_datetime']).isoformat()

#endregion

#region Collection management

async def get_or_init_flight_data_collection() -> AgnosticCollection:

    async def create_collection(db: AgnosticDatabase, n: str):
        collection = await db.create_collection(n, timeseries = {
            'timeField': '_start_time',
            'metaField': 'metadata',
            'granularity': 'seconds'
        }) # type: ignore
        await collection.create_index([("metadata._flight_id", DESCENDING),
                                      ("metadata.part_id", ASCENDING)])
        return collection

    col = await get_or_init_collection(f'flight_data_compact', create_collection)
    return col


#endregion

# Inserts new measured flight data
async def insert_flight_data(measurements: list[FlightMeasurementCompactDB], flight_id: UUID):

    insert_start_time = time()

    collection = await get_or_init_flight_data_collection()

    # Convert into a datetime object, because mongodb
    # suddenly wants datetime objects instead of strings here
    measurements_raw = [m.model_dump(by_alias=True) for m in measurements]

    for m in measurements_raw:
        m['_start_time'] = m['_start_time']
        m['metadata'] = {'_flight_id': flight_id, 'part_id': m['part_id']}
        del m['part_id']

    write_start_time = time()

    res = await collection.insert_many(measurements_raw) # type: ignore

    after_write_time = time()
    preparation_time = write_start_time - insert_start_time
    db_time = after_write_time - write_start_time

    # current_app.logger.debug(f'Pushed {len(measurements)} compact measurements. Total: {int((preparation_time + db_time)*1000)}ms; Preparation {int((preparation_time)*1000)}ms; DB: {int((db_time)*1000)}ms;')

    s = cast(NamedSignal, signal(NEW_FLIGHT_DATA_COMPACT))

    s.send(None, flight_id=flight_id, measurements = measurements) # type: ignore

async def get_flight_data_in_range(series_identifier: FlightMeasurementSeriesIdentifier, start: datetime, end: datetime) -> list[FlightMeasurement]:
    collection = await get_or_init_flight_data_collection()

    # Get all measurements in the date range
    res = await collection.find({'_start_time': { '$gte': start, '$lt': end }, 'metadata._flight_id': {'$eq': series_identifier.flight_id}, 'metadata.part_id': {'$eq': series_identifier.vessel_part_id}  }).to_list(1000)

    debsonify_measurements(res)

    for m in res:
        del m['_id']
        m['part_id'] = series_identifier.vessel_part_id
        
        if isinstance(m['_start_time'], datetime):
            m['_start_time'] = m['_start_time'].isoformat()
        if isinstance(m['_end_time'], datetime):
            m['_end_time'] = m['_end_time'].isoformat()

        del m['metadata']

    return [FlightMeasurement(**r) for r in res]

async def get_aggregated_flight_data(series_identifier: FlightMeasurementSeriesIdentifier, start: datetime, end: datetime, resolution: Literal['year', 'month', 'day', 'hour', 'minute', 'second', 'decisecond'], schemas: list[FlightMeasurementDescriptor] ):

    match_stage = {
        '$match': {
            '_start_time': { '$gte': start, '$lt': end },
            'metadata._flight_id': {'$eq': series_identifier.flight_id}
        }
    }

    if series_identifier.vessel_part_id is not None:
        match_stage['$match']['metadata.part_id'] = {'$eq': series_identifier.vessel_part_id}

    group_stage = {
        '$group': {
            '_id': {
                'date': get_date_grouping(resolution)
            },
            '_start_time': {'$min': '$_start_time'},
            '_end_time': {'$max': '$_start_time'}
        }
    }

    group_stage['$group'].update(get_averaging(schemas))

    project_aggregated_stage = {
        '$project': {
            'measurements_aggregated': { 
            },
            '_start_time': '$_start_time',
            '_end_time': '$_end_time'
        }
    }

    project_aggregated_stage['$project']['measurements_aggregated'].update(get_aggregated_result_projection(schemas))

    collection = await get_or_init_flight_data_collection()

    res = await collection.aggregate([match_stage, project_stage, group_stage, project_aggregated_stage]).to_list(1000)

    # res = list(collection.aggregate(dummy))
    
    debsonify_measurements(res)
    
    for m in res:
        del m['_id']
        m['part_id'] = series_identifier.vessel_part_id
        m['_start_time'] = m['_start_time'].isoformat()
        m['_end_time'] = m['_end_time'].isoformat()
        
        # del m['metadata']
    
    return [FlightMeasurementCompactDB(**r) for r in res]
