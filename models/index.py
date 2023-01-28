from models.command import CommandSchema
from models.flight import FlightSchema
from models.flight_measurement import FlightMeasurementSeriesIdentifierSchema, FlightMeasurementSchema, FlightMeasurementDescriptorSchema
from models.vessel_part import VesselPartSchema
from models.vessel import VesselSchema

all_models = [CommandSchema, FlightMeasurementSchema, FlightMeasurementSeriesIdentifierSchema, FlightSchema, VesselPartSchema, VesselSchema]