from motor.core import AgnosticDatabase, AgnosticCollection
from ..mongodb.mongodb_connection import get_db
from typing import Any, Callable, Coroutine
from logging import Logger

cached_collections = dict()

async def get_or_init_collection(name: str, create_collection_func: Callable[[AgnosticDatabase, str], Coroutine[Any, Any, AgnosticCollection]] ) -> AgnosticCollection:
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

        existing_collection = await db.list_collection_names(filter = { 'name': { '$eq': name }})

        # If the collection already exist we are done
        if len(existing_collection) > 0:
            cached_collections[name] = True
            return db[name]

        # Loop around if the creation failed
        try:
            await create_collection_func(db, name)
        except Exception as e:
            # Logger.error(e.args[0])
            continue

        cached_collections[name] = True
        return db[name]
    
    raise RuntimeError()