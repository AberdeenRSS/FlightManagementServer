from dataclasses import dataclass, field
from datetime import datetime
from typing import Union
from uuid import UUID
from marshmallow import Schema, fields
from models.flight_measurement import FlightMeasurement, FlightMeasurementDescriptorSchema
from models.vessel import VesselSchema
from helper.model_helper import make_safe_schema

@dataclass
class Flight:

    _id: UUID
    """
    The id of the flight. (Primary identifier)
    """

    _vessel_id: UUID
    """
    The id of the vessel that is performing this flight
    """

    _vessel_version: int
    """
    The version of the vessel this flight was based on
    This is important if the vessel gets modified later to make
    sure all the flight information can still be matched up accordingly
    """

    name = ""

    start: datetime
    """
    When the flight started
    """

    end: Union[datetime, None] = None
    """
    When the flight ended
    """

    measured_parts: dict[str, list[FlightMeasurement]] = field(default_factory=dict)
    """
    The list of vessel parts that have measurements for and how those measurements will look like
    """

class FlightSchema(make_safe_schema(Flight)):

    _id = fields.UUID(required = True)
    """
    The id of the flight. (Primary identifier)
    """

    _vessel_id = fields.UUID(required = True)
    """
    The id of the vessel that is performing this flight
    """

    _vessel_version = fields.Int(required = True)
    """
    The version of the vessel this flight was based on
    This is important if the vessel gets modified later to make
    sure all the flight information can still be matched up accordingly
    """

    name = fields.Str()

    start = fields.DateTime(required = True)
    """
    When the flight started
    """

    end = fields.DateTime()
    """
    When the flight ended
    """

    measured_parts = fields.Dict(keys= fields.Str(), values= fields.List(fields.Nested(FlightMeasurementDescriptorSchema)))
    """
    The list of vessel parts that have measurements for and how those measurements will look like
    """

