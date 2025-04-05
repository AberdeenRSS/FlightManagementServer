from contextlib import asynccontextmanager
import gzip
from app.controller.auth_controller import auth_controller
from app.controller.command_controller import command_controller
from app.controller.vessel_controller import vessel_controller,vessels_controller
from app.controller.user_controller import user_controller
from app.controller.flight_data_controller import flight_data_controller
from app.controller.flight_controller import flight_controller, flights_controller
# from app.mqtt.oauth_plugin import OAuthPlugin
from app.mqtt.init_mqtt import start_mqtt, stop_mqtt
from app.services.data_access.mongodb.mongodb_connection import init_app
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import Message
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware


# logging.basicConfig(level=logging.DEBUG)

class GZipedMiddleware(BaseHTTPMiddleware):
    async def set_body(self, request: Request):
        receive_ = await request._() # type: ignore
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

@asynccontextmanager
async def _lifetime(app: FastAPI):
    
    try:
        start_mqtt(app, 'localhost')
        yield
    finally:
        stop_mqtt()


# Init fast api
app = FastAPI(lifespan=_lifetime)
# app.add_middleware(GZipedMiddleware)

init_app(app)

app.include_router(auth_controller)
app.include_router(command_controller)
app.include_router(vessel_controller)
app.include_router(vessels_controller) # /v1/
app.include_router(flights_controller) # /v1/
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


# # Define MQTT broker configuration
# config = {
#     "listeners": {
#         "default": {
#             "type": "tcp",
#             "bind": "0.0.0.0:1883",
#         },
#     },
#     "sys_interval": 60,
#     "topic-check": {
#         "enabled": False,
#         "plugins": ['oauth'],
#     },
# }

# broker = Broker(config)

# Plugin = namedtuple("Plugin", ["name", "ep", "object"])


# plugin_context = copy.copy(broker.plugins_manager.app_context)
# obj = OAuthPlugin(plugin_context)
# plugin = Plugin('auth.oauth', None, obj)

# broker.plugins_manager.plugins.append(plugin)

# Create an async function to start the broker
# @app.on_event("startup")
# async def start_broker():
#     await broker.start()

# # Create an async function to stop the broker
# @app.on_event("shutdown")
# async def stop_broker():
#     await broker.shutdown()


# Use FastAPI to serve your MQTT broker

# init_app(app) 

# if __name__ == '__main__':
#     start_fast_api()
