from typing import Any, Mapping
from flask import current_app, g
from pymongo import MongoClient
from pymongo.database import Database

connection_string = None

# Provide the mongodb atlas url to connect python to mongodb using pymongo
full_connection_string = None

def get_db() -> Database:

    # Case for when there is no global context available
    # e.g. during setup
    if not g:
        client = MongoClient(full_connection_string)
        return client['rocketry']

    if 'db' not in g:
        # Create a connection using MongoClient
        client = MongoClient(full_connection_string)
        g.db = client
        
    return g.db['rocketry']

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_app(app):
    global full_connection_string
    connection_string = app.config.get('connection_string') or 'mongodb://localhost:27017' 
    full_connection_string = f"{connection_string}/rocketDatabase1"
    app.teardown_appcontext(close_db)