
import signal
from typing import Any
from __init__ import create_app 
from os import environ
import uvicorn
import socketio
import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve


def make_app():

    debug = bool(environ.get('FLIGHT_MANAGEMENT_SERVER_DEBUG'))

    print(f'Starting server in {"Debug" if debug else "Production"} mode...')

    config = Config()
    config.bind = ["localhost:5000"]  # As an example configuration setting
    config.debug = debug
    config.graceful_timeout 

    flask_app, socket_io_server = create_app(debug)

    app = socketio.ASGIApp(socket_io_server, flask_app)

    asyncio.run(serve(app, config))



if __name__ == '__main__':
    make_app()