from datetime import datetime
from typing import Any, List, Literal, Sequence, cast
from uuid import UUID
from motor.core import AgnosticCollection, AgnosticDatabase
from pymongo import ASCENDING, DESCENDING
from app.models.flight_measurement import FlightMeasurementAggregated, FlightMeasurementDB, FlightMeasurementSeriesIdentifier
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
        'first': { '$arrayElemAt': [ "$measurements", 0 ] },
        'last': { '$arrayElemAt': [ "$measurements", -1 ] },
        'p_index': "$metadata.p_index",
        'm_index': "$metadata.m_index",
        'min': '$min',
        'avg': '$avg',
        'max': '$max',
        '_start_time': '$_start_time',
        '_end_time': '$_end_time'
    }
}

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

def debsonify_measurements(measurements: list[dict]):
    for r in measurements:
        r['_id'] = str(r['_id'])
        if '_datetime' in r:
            r['_datetime'] = cast(datetime, r['_datetime']).isoformat()

#endregion

#region Collection management

async def get_or_init_flight_data_collection(table: str = 'flight_data') -> AgnosticCollection:

    async def create_collection(db: AgnosticDatabase, n: str):
        collection = await db.create_collection(n, timeseries = {
            'timeField': '_start_time',
            'metaField': 'metadata',
            'granularity': 'seconds'
        }) # type: ignore
        await collection.create_index([
            ("metadata._flight_id", DESCENDING),
            ("metadata.part_id", ASCENDING),
            ("metadata.m_index", ASCENDING),
        ])
        return collection

    col = await get_or_init_collection(table, create_collection)
    return col

#endregion

async def insert_flight_data(measurements: list[FlightMeasurementDB], flight_id: UUID, table: str = 'flight_data'):

    insert_start_time = time()

    collection = await get_or_init_flight_data_collection(table)

    # Convert into a datetime object, because mongodb
    # suddenly wants datetime objects instead of strings here
    measurements_raw = [m.model_dump(by_alias=True) for m in measurements]

    for m in measurements_raw:
        m['_start_time'] = m['_start_time']
        m['metadata'] = {'_flight_id': flight_id, 'p_index': m['p_index'], 'm_index': m['m_index']}
        del m['p_index']
        del m['m_index']

    write_start_time = time()

    res = await collection.insert_many(measurements_raw) # type: ignore

    after_write_time = time()
    preparation_time = write_start_time - insert_start_time
    db_time = after_write_time - write_start_time

    # current_app.logger.debug(f'Pushed {len(measurements)} compact measurements. Total: {int((preparation_time + db_time)*1000)}ms; Preparation {int((preparation_time)*1000)}ms; DB: {int((db_time)*1000)}ms;')


async def get_flight_data_in_range(series_identifier: FlightMeasurementSeriesIdentifier, start: datetime, end: datetime, table: str = 'flight_data') -> list[FlightMeasurementDB]:
    collection = await get_or_init_flight_data_collection(table)

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

    return [FlightMeasurementDB(**r) for r in res]

async def get_aggregated_flight_data(flight_id: UUID, part_index: int | None, measurement_index: int | None, start: datetime, end: datetime, resolution: Literal['year', 'month', 'day', 'hour', 'minute', 'second', 'decisecond'], schemas: Any, table: str = 'flight_data') -> list[FlightMeasurementAggregated]:

    match_stage = {
        '$match': {
            '_start_time': { '$gte': start, '$lt': end },
            'metadata._flight_id': {'$eq': flight_id}
        }
    }

    if part_index is not None:
        match_stage['$match']['metadata.p_index'] = {'$eq': part_index }

    if measurement_index is not None:
        match_stage['$match']['metadata.m_index'] = {'$eq': measurement_index }

    group_stage = {
        '$group': {
            '_id': {
                'date': get_date_grouping(resolution),
                'p_index': '$p_index',
                'm_index': '$m_index'
            },
            '_start_time': {'$min': '$_start_time'},
            '_end_time': {'$max': '$_start_time'},
            'min': {'$min': '$min'},
            'avg': {'$avg': '$avg'},
            'max': {'$max': '$max'},
            'first': { '$first': '$first' },
            'last': { '$last': '$last' },
        }
    }


    # project_aggregated_stage = {
    #     '$project': {
    #         'measurements_aggregated': { 
    #         },
    #         '_start_time': '$_start_time',
    #         '_end_time': '$_end_time'
    #     }
    # }

    # project_aggregated_stage['$project']['measurements_aggregated'].update(get_aggregated_result_projection(schemas))

    collection = await get_or_init_flight_data_collection(table)

    res = await collection.aggregate([match_stage, project_stage, group_stage]).to_list(1000)

    # res = list(collection.aggregate(dummy))
    
    # debsonify_measurements(res)
    
    for m in res:
        m['p_index'] = m['_id']['p_index']
        m['m_index'] = m['_id']['m_index']
        m['_start_time'] = m['_start_time'].isoformat()
        m['_end_time'] = m['_end_time'].isoformat()
        m['series_name'] = None
        m['part_id'] = None
        del m['_id']
            
    return [FlightMeasurementAggregated(**r) for r in res]

async def bulk_delete_flight_data_by_flight_ids(_ids: List[UUID]) -> bool:
    flight_data_collection = await get_or_init_flight_data_collection("flight_data")
    results = await flight_data_collection.delete_many({'metadata._flight_id': {'$in': _ids}})
    
    return results.deleted_count > 0

async def bulk_delete_flight_commands_by_flight_ids(_ids: List[UUID]) -> bool:
    commands_collection = await get_or_init_flight_data_collection("commands")  
    results = await commands_collection.delete_many({'metadata._flight_id': {'$in': _ids}})

    return results.deleted_count > 0
        
    