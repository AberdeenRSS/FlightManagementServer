from datetime import datetime, timezone
from typing import Any, Union
from uuid import UUID
from pydantic import BaseModel, Field

from app.helper.datetime_model import AwareDatetimeModel

class Command(AwareDatetimeModel):
    """
    Commands are issued to vessels to make them perform and action
    The vessel's computer has to retrieve them and report if they where
    completed successfully
    """

    id: UUID = Field(..., alias='_id')
    """
    The id of the command itself. This is to identify the command. Every new subsequent
    command needs a new id to distinguish it
    """

    command_type: str = Field(alias='_command_type', alias_priority=1, default=None)
    """The code that identifies the command, i.e. what action should be performed"""

    create_time: datetime
    """Time at which the command was created"""

    part_id: Union[UUID, None] = Field(alias='_part_id', alias_priority=1, default=None) 
    """
    The id of the part that the command is for (Optional if the command is for the entire vessel)
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

    state: str = "new"
    """The state the command is in as known by the server"""

    command_payload: Union[None, Any] = None
    """The payload data of the command. Can be any arbitrary additional data specifying what exactly should happen"""

    response_message: str = ''
    """Free text for a response message. Meant for human readable information"""

    response: Union[None, Any] = None
    """
    Response by the vessel, detailing how the command was processed
    If the the command failed, this should contain the reason why
    """

class CommandInfo(BaseModel):
    """Info on th shape of commands"""

    name: str

    payload_schema: None | str | list[tuple[str, str]]

