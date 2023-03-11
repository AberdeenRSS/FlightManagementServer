
from __init__ import create_app 
from os import environ

if __name__ == '__main__':

    debug = bool(environ.get('FLIGHT_MANAGEMENT_SERVER_DEBUG'))

    print(f'Starting server in {"Debug" if debug else "Production"} mode...')

    app, socketio = create_app(debug)

    socketio.run(app, debug=debug, host='0.0.0.0')