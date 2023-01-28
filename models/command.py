from dataclasses import dataclass
from datetime import datetime
from typing import Any, Union
from uuid import UUID
from marshmallow import Schema, fields, validate
from helper.model_helper import make_safe_schema

@dataclass
class Command:
    """
    Commands are issued to vessels to make them perform and action
    The vessel's computer has to retrieve them and report if they where
    completed successfully
    """

    _id: UUID
    """
    The id of the command itself. This is to identify the command. Every new subsequent
    command needs a new id to distinguish it
    """

    command_code: str
    """The code that identifies the command, i.e. what action should be performed"""

    create_time: datetime
    """Time at which the command was created"""

    part_id: Union[UUID, None] = None
    """
    The id of the part that the command is for (Optional)
    """

    dispatch_time: Union[datetime, None] = None
    """
    Time at which the command was dispatched to the vessel
    If not set, the command was not yet dispatched
    """

    receive_time: Union[datetime, None] = None
    """
    Time at which the command was received by the vessel
    If not set, the command was not yet received by the vessel
    """

    complete_time: Union[datetime, None] = None
    """
    Time at which the vessel confirmed the successful or unsuccessful execution of the command
    If not set, the command was yet completed or it failed
    """

    state = "new"
    """The state the command is in as known by the server"""

    command_payload: Union[None, Any] = None
    """The payload data of the command. Can be any arbitrary additional data specifying what exactly should happen"""

    response: Union[None, Any] = None
    """
    Response by the vessel, detailing how the command was processed
    If the the command failed, this should contain the reason why
    """

class CommandSchema(make_safe_schema(Command)):
    """
    Commands are issued to vessels to make them perform and action
    The vessel's computer has to retrieve them and report if they where
    completed successfully
    """

    _id = fields.UUID(required = True)
    """
    The id of the command itself. This is to identify the command. Every new subsequent
    command needs a new id to distinguish it
    """

    part_id = fields.UUID()
    """
    The id of the part that the command is for (Optional)
    """

    command_code = fields.String(required = True)
    """The code that identifies the command, i.e. what action should be performed"""

    create_time = fields.DateTime(required = True)
    """Time at which the command was created"""

    dispatch_time = fields.DateTime()
    """
    Time at which the command was dispatched to the vessel
    If not set, the command was not yet dispatched
    """

    receive_time = fields.DateTime()
    """
    Time at which the command was received by the vessel
    If not set, the command was not yet received by the vessel
    """

    complete_time = fields.DateTime()
    """
    Time at which the vessel confirmed the successful or unsuccessful execution of the command
    If not set, the command was yet completed or it failed
    """

    state = fields.String(required = True, validate= validate.Regexp(r"(new)|(dispatched)|(received)|(completed)|(failed)"))
    """The state the command is in as known by the server"""

    command_payload = fields.Raw()
    """The payload data of the command. Can be any arbitrary additional data specifying what exactly should happen"""

    response = fields.Raw()
    """
    Response by the vessel, detailing how the command was processed
    If the the command failed, this should contain the reason why
    """