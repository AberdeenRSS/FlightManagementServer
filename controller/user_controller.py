from dataclasses import dataclass
import datetime
from os import environ
from typing import Dict, List
from quart import Blueprint, request
import httpx
import urllib.parse
from middleware.auth.requireAuth import auth_required
from models.auth_models import LoginModel, RegisterModel
from models.authorization_code import TokenPair, TokenPairSchema
from models.user import User, hash_password
from services.data_access.auth_code import create_auth_code
from uuid import UUID, uuid4
from services.auth.jwt_auth_service import generate_access_token, generate_refresh_token

from services.data_access.user import get_user, get_users, get_users_by_name, create_or_update_user
from services.data_access.auth_code import get_code, delete_code

from quart_schema import DataSource, documentation
import quart_schema
from pydantic import RootModel, StringConstraints

user_controller = Blueprint('user', __name__, url_prefix='/user')

@user_controller.route("/get_names", methods=['GET'])
@quart_schema.validate_request([RootModel[List[UUID]]])
@quart_schema.validate_response(RootModel[Dict[UUID, str]])
@quart_schema.security_scheme([])
async def register(data: list[UUID]):

    users = await get_users(data)

    return dict([(u._id, u.name) for u in users])

