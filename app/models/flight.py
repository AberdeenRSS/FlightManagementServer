from dataclasses import dataclass, field
from datetime import datetime, timedelta
from datetime import timezone
from typing import Dict, Union
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from app.helper.datetime_model import AwareDatetimeModel
from app.models.command import CommandInfo
from app.models.flight_measurement import FlightMeasurement, FlightMeasurementDescriptor

FLIGHT_DEFAULT_HEAD_TIME = timedelta(minutes=2)
"""
A flight that is still ongoing gets this amount of time
added to its end time from utcnow by default
"""

FLIGHT_MINIMUM_HEAD_TIME = timedelta(minutes=1)
"""
This is the minimum time the end of a flight can be ahead,
before it needs to be extended
"""

class Flight(AwareDatetimeModel):

    start: datetime
    """
    When the flight started
    """

    id: UUID = Field(..., alias='_id', default_factory=uuid4)
    """
    The id of the flight. (Primary identifier)
    """

    vessel_id: UUID = Field(alias='_vessel_id', alias_priority=1, default=None)
    """
    The id of the vessel that is performing this flight
    """

    vessel_version: int = Field(alias='_vessel_version', alias_priority=1, default=0)
    """
    The version of the vessel this flight was based on
    This is important if the vessel gets modified later to make
    sure all the flight information can still be matched up accordingly
    """

    name: str = ""

    end: Union[datetime, None] = None
    """
    When the flight ended
    """

    measured_part_ids: list[str] = Field(default_factory=list)

    measured_parts: dict[str, list[FlightMeasurementDescriptor]] = Field(default_factory=dict)
    """
    The list of vessel parts that have measurements for and how those measurements will look like
    """

    available_commands: dict[str, list[CommandInfo]] = Field(default_factory=dict)
    """
    list of commands available on each part.
    """

    permissions: dict[str, str] = Field(default_factory=dict)
    """
    User id permission pairs of who has what permission on the vessel
    """

    no_auth_permission: Union[None, str] = 'none'
    """
    The permission everyone has regardless of if they are logged in or not
    """


class UpdateFlight(BaseModel):
    name: str
    """
    The name of the flight
    """
