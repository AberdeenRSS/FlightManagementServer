from pymongo import database, collection
from services.data_access.mongodb.mongodb_connection import get_db
from typing import Callable
from flask import current_app

cached_collections = dict()

def get_or_init_collection(name: str, create_collection_func: Callable[[database.Database, str], collection.Collection] ) -> collection.Collection:
    """ 
    Gets or inits a mongo db collection with the provided name. First looks into a memory cache if the collection
    was already created, if not makes a database request to find out. If the collection still doesn't exist tries
    to create it by calling the provided method. if the creation failed loops around another time to get the now
    hopefully created one
    """

    global cached_collections

    db = get_db()

    for i in range(0, 2):

        if name in cached_collections:
            return db[name]

        existing_collection = db.list_collection_names(filter = { 'name': { '$eq': name }})

        # If the collection already exist we are done
        if len(existing_collection) > 0:
            cached_collections[name] = True
            return db[name]

        # Loop around if the creation failed
        try:
            create_collection_func(db, name)
        except Exception as e:
            current_app.logger.warn(f'Collection creation failed. Retry ({i})... Error encountered {e}')
            continue

        cached_collections[name] = True
        return db[name]
    
    raise RuntimeError()