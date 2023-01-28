from typing import cast
from uuid import UUID, uuid4
from flask import Blueprint
from flask import request, flash, g, jsonify
from middleware.auth.requireAuth import auth_required

from models.vessel import VesselSchema, Vessel
from services.auth.jwt_user_info import User, get_user_info
from services.data_access.vessel import create_or_update_vessel, get_all_vessels



vessel_api = Blueprint('vessel', __name__, url_prefix='/vessel')

# Method for a vessel to register
@vessel_api.route("/register", methods = ['POST'])
@auth_required
def registerVessel():

    vessel = VesselSchema().load_safe(Vessel, request.get_json())
    user_info = cast(User, get_user_info())

    # Use the identity of the vessel as its id -> Only one entry per authentication code
    vessel._id = UUID(user_info.unique_id)

    acc = create_or_update_vessel(vessel)

    return VesselSchema().dumps(acc)

@vessel_api.route("/get_all", methods = ['GET'])
@auth_required
def get_all():
    vessels = get_all_vessels()
    return VesselSchema(many=True).dumps(vessels)

@vessel_api.route("/get_test_vessels", methods = ['GET'])
def get_test_vessels():
    """
    Returns a test response. Returned vessel gets a new random uuid
    ---
    tags:
      - vessel
    responses:
      200:
        description: The test vessel
        schema:
          $ref: "#/definitions/Vessel"
    """

    vessel = Vessel(_id = uuid4(), _version = 1)
    vessel.name = 'Test vessel'
    return VesselSchema().dumps(vessel)


