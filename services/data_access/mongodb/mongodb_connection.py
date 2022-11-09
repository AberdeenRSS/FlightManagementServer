from flask import current_app, g
from pymongo import MongoClient
from pymongo.database import Database

# Provide the mongodb atlas url to connect python to mongodb using pymongo
CONNECTION_STRING = "mongodb://localhost:27017/rocketDatabase1"

def get_db() -> Database:

    # Case for when there is no global context available
    # e.g. during setup
    if not g:
        client = MongoClient(CONNECTION_STRING)
        return client['rocketry']

    if 'db' not in g:
        # Create a connection using MongoClient
        client = MongoClient(CONNECTION_STRING)
        g.db = client
        
    return g.db['rocketry']

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)