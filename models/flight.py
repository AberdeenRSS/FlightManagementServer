from schematics.models import Model
from schematics.types import StringType, UUIDType, DateTimeType, ListType, ModelType, IntType, DictType
from models.flight_measurement import FlightMeasurementSchema

from models.vessel import Vessel


class Flight(Model):

    # The id of the Flight
    _id = UUIDType(required = True)

    # The id of the vessel (Part of the primary key)
    _vessel_id = UUIDType(required = True)

    # The version of the vessel this flight was based on
    # This is important if the vessel gets modified later to make
    # sure all the flight information can still be matched up accordingly
    _vessel_version = IntType(required = True)

    # The name of the Flight
    name = StringType()

    # Start time of the flight
    start = DateTimeType(required = True)

    # End time of the flight
    end = DateTimeType()

    # The list of vessel parts that have measurements
    # for 
    measured_parts = DictType(ListType(ModelType(FlightMeasurementSchema)))

