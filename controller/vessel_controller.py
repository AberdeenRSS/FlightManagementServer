from flask import Blueprint
from flask import request, flash, g, jsonify
from helper.model_helper import export_list
from middleware.auth.requireAuth import auth_required

from models.vessel import Vessel
from services.auth.jwt_user_info import get_user_info
from services.data_access.vessel import create_or_update_vessel, get_all_vessels


vessel_api = Blueprint('vessel', __name__, url_prefix='/vessel')

# Method for a vessel to register
@vessel_api.route("/register", methods = ['POST'])
@auth_required
def registerVessel():

    vessel = Vessel(request.get_json())
    user_info = get_user_info()

    # Use the identity of the vessel as its id -> Only one entry per authentication code
    vessel._id = user_info.unique_id

    vessel.validate()

    acc = create_or_update_vessel(vessel)

    return jsonify(acc.to_primitive())

@vessel_api.route("/get_all", methods = ['GET'])
@auth_required
def get_all():
    vessels = get_all_vessels()
    return jsonify(export_list(vessels))

@vessel_api.route("/get_test_vessels", methods = ['GET'])
@auth_required
def get_test_vessels():
    return jsonify([{'name': 'a vessel'}])

@vessel_api.route("/stupid_calculator", methods = ['GET'])
def stupid_calculator():
    return request.args['a'] + request.args['b']

