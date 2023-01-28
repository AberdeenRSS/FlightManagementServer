from datetime import datetime
from typing import cast
from flask import Blueprint
from flask import request, flash, g, jsonify
from middleware.auth.requireAuth import auth_required
from uuid import uuid4

from models.command import CommandSchema
from services.auth.jwt_user_info import User, get_user_info
from services.data_access.command import insert_commands
from services.data_access.vessel import get_vessel


command_controller = Blueprint('command', __name__, url_prefix='/command')

@command_controller.route("/dispatch/<flight_id>", methods = ['POST'])
@auth_required
def dispatch_commands(flight_id: str):
    """
    Dispatches a command to the vessel. Meant to be called from a ui/frontend or
    other type of client
    """

    parsed_commands = request.get_json()

    if not isinstance(parsed_commands, list):
        flash('Invalid json, commands have to be send as an array')
        return ''
    
    commands = import_list(parsed_commands, CommandSchema)

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