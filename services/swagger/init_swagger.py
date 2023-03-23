from quart import Quart, request
from flasgger import Swagger, LazyString, LazyJSONEncoder
from flasgger import swag_from
from quart import Quart
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from flasgger import APISpec, Swagger
from models.index import all_models

def init_swagger(app: Quart):


    plugins = [FlaskPlugin(), MarshmallowPlugin()]
    spec = APISpec("My api docs", '1.0', "2.0", plugins=plugins)
    template = spec.to_flasgger(app, definitions=all_models)

    template['specs_route'] = "/apidocs/"
    swagger =  Swagger(app, template=template, parse=False)

    return swagger
 