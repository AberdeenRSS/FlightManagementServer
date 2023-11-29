
from .services.data_access.init import init_data_access
from .services.data_access.mongodb.mongodb_connection import init_app
from .controller.auth_controller import auth_controller

from fastapi import FastAPI


app = FastAPI()

app.include_router(auth_controller)


# if __name__ == '__main__':
#     start_fast_api()