
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
    dockerized = bool(environ.get('DOCKERIZED'))

    print(f'dockerized: {dockerized}')

    print(f'Starting server in {"Debug" if debug else "Production"} mode...')

    config = Config()
    config.bind = ["0.0.0.0:5000" if dockerized else "0.0.0.0:5000"] 
    # config.bind = ['0.0.0.0:5000', 'localhost:5000']
    config.debug = debug
    config.workers = 10 

    flask_app, socket_io_server = create_app(debug)

    app = socketio.ASGIApp(socket_io_server, flask_app)

    asyncio.run(serve(app, config))



if __name__ == '__main__':
    make_app()