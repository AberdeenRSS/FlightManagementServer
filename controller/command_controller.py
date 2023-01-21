from datetime import datetime
from typing import cast
from flask import Blueprint
from flask import request, flash, g, jsonify
from helper.model_helper import export_list
from middleware.auth.requireAuth import auth_required
from uuid import uuid4

from helper.model_helper import import_list
from models.command import Command
from services.auth.jwt_user_info import User, get_user_info
from services.data_access.command import insert_commands
from services.data_access.vessel import get_vessel
from schematics.types import StringType, UUIDType, DateTimeType, ListType, ModelType, BaseType, DictType, NumberType, IntType, FloatType



command_controller = Blueprint('command', __name__, url_prefix='/command')

# Method for a vessel to register
@command_controller.route("/dispatch/<flight_id>", methods = ['POST'])
@auth_required
def dispatch_commands(flight_id: str):

    parsed_commands = request.get_json()

    if not isinstance(parsed_commands, list):
        flash('Invalid json, commands have to be send as an array')
        return ''
    
    commands = import_list(parsed_commands, Command)

    if len(commands) < 1:
        flash('No command in list')
        return ''

    user_info = cast(User, get_user_info())

    for command in commands:
        command.validate()
        assert command.state == 'new'
        assert command.create_time
        assert cast(datetime, command.create_time) < datetime.now()
        assert command.dispatch_time == None
        assert command.receive_time == None
        assert command.complete_time == None

    insert_commands(commands, flight_id)

    return ''