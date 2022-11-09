from typing import Any, Union

command_state_new = 'new'
command_state_dispatched = 'dispatched'
command_state_completed = 'completed'
command_state_failed = 'failed'

# Commands are issued to vessels to make them perform and action
# The vessel's computer has to retrieve them and report if they where
# completed successfully
class Command:

    # The id of the command itself. This is to identify the command. Every new subsequent
    # command needs a new id to distinguish it
    _id: str = ''

    # The id of the flight the command is performed in (Part of the primary key)
    _flight_id: str = ''

    # The id of the part that the command is for (Optional)
    part_id: Union[str, None] = None

    # The code that identifies the command, i.e. what action should be performed
    command_code: str = ''

    # The execution state of the command:
    #   'new'       : The command was created, but not processed in any way yet
    #   'dispatched': The command was dispatched to the vessel
    #   'completed' : The command was completed successfully
    #   'failed'    : There was a problem executing the command
    state: Union[command_state_new, command_state_dispatched, command_state_completed, command_state_failed] = 'new'

    # The payload data of the command. Can be any arbitrary additional data specifying what exactly should happen
    command_payload: Union[Any, None] = None

    # Response by the vessel, detailing how the command was processed
    # If the the command failed, this should contain the reason why
    response: Union[str, None] = None