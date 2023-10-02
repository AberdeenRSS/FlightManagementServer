from quart import Quart, Request

from quart_schema import QuartSchema, Info

def init_swagger(app: Quart):

    return QuartSchema(app, info=Info(title="Flight Management Server", version='0.0.1'))
 