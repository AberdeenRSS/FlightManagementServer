from typing import Any, Union
from schematics.models import Model
from schematics.types import StringType, UUIDType, DateTimeType, ListType, ModelType, BaseType, DictType, NumberType, IntType, FloatType

# Commands are issued to vessels to make them perform and action
# The vessel's computer has to retrieve them and report if they where
# completed successfully
class Command(Model):

    # The id of the command itself. This is to identify the command. Every new subsequent
    # command needs a new id to distinguish it
    _id = UUIDType(required = True)

    # The id of the part that the command is for (Optional)
    part_id = UUIDType()

    # The code that identifies the command, i.e. what action should be performed
    command_code = StringType(required = True)

    # Time at which the command was created
    create_time = DateTimeType(required = True)

    # Time at which the command was dispatched to the vessel
    # If not set, the command was not yet dispatched
    dispatch_time = DateTimeType()

    # Time at which the command was received by the vessel
    # If not set, the command was not yet received by the vessel
    receive_time = DateTimeType()

    # Time at which the vessel confirmed the successful or unsuccessful execution of the command
    # If not set, the command was yet completed or it failed
    complete_time = DateTimeType()

    # The state the command is in as known by the server
    state = StringType(required = True, regex = r"(new)|(dispatched)|(received)|(completed)|(failed)")

    # The payload data of the command. Can be any arbitrary additional data specifying what exactly should happen
    command_payload = DictType(BaseType)

    # Response by the vessel, detailing how the command was processed
    # If the the command failed, this should contain the reason why
    response = DictType(BaseType)