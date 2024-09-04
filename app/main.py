import gzip
from app.controller.auth_controller import auth_controller
from app.controller.command_controller import command_controller
from app.controller.socketio.init import init_socket_io_controller
from app.controller.vessel_controller import vessel_controller
from app.controller.user_controller import user_controller
from app.controller.flight_data_controller import flight_data_controller
from app.controller.flight_controller import flight_controller
from app.helper.json_helper import PlainJsonSerializer
from app.services.data_access.mongodb.mongodb_connection import init_app
from fastapi import FastAPI
import socketio
from fastapi.middleware.cors import CORSMiddleware

from starlette.types import Message
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware

class GZipedMiddleware(BaseHTTPMiddleware):
    async def set_body(self, request: Request):
        receive_ = await request._()
        if "gzip" in request.headers.getlist("Content-Encoding"):
            body = receive_.get('body')
            if isinstance(body, bytes):
                data = gzip.decompress(body)
            receive_['body'] = data

        async def receive() -> Message:
            return receive_

        request._receive = receive                

    async def dispatch(self, request, call_next):
        await self.set_body(request)        
        response = await call_next(request)                
        return response

def socketio_mount(
    app: FastAPI,
    async_mode: str = "asgi",
    mount_path: str = "/socket.io/",
    socketio_path: str = "socket.io",
    logger: bool = False,
    engineio_logger: bool = False,
    cors_allowed_origins="*",
    **kwargs
) -> socketio.AsyncServer:
    """Mounts an async SocketIO app over an FastAPI app."""

    sio = socketio.AsyncServer(async_mode=async_mode,
                      cors_allowed_origins=cors_allowed_origins,
                      logger=logger,
                      json=PlainJsonSerializer,
                      engineio_logger=engineio_logger, **kwargs)

    sio_app = socketio.ASGIApp(sio, socketio_path=socketio_path)

    # mount
    app.add_route(mount_path, route=sio_app, methods=["GET", "POST"])
    app.add_websocket_route(mount_path, sio_app)

    return sio

# Init socketio app

# Init fast api
app = FastAPI()
# app.add_middleware(GZipedMiddleware)

init_app(app)

app.include_router(auth_controller)
app.include_router(command_controller)
app.include_router(vessel_controller)
app.include_router(flight_controller)
app.include_router(flight_data_controller)
app.include_router(user_controller)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sio = socketio_mount(app)

init_socket_io_controller(sio)

# init_app(app)

# if __name__ == '__main__':
#     start_fast_api()
