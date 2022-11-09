from time import strftime
import uuid
from schematics.models import Model
from schematics.types import StringType, UUIDType, DateTimeType, ListType, ModelType, BaseType, DictType, NumberType, IntType, FloatType

# Identifies which time series the measurement belongs to
class FlightMeasurementSeriesIdentifier(Model):
    # The id of the flight
    _flight_id = UUIDType(required = True)

    # The vessel part the measurement is for
    _vessel_part_id = UUIDType(required = True)

# Describes a field in the measured data
class FlightMeasurementSchema(Model):
    # The name of the datefield
    name = StringType()

    # The type of that data field
    type = StringType(r"(string)|(int)|(float)")

# A single measurement relayed back by the model
class FlightMeasurement(Model):

    # Database index
    _id = StringType()

    # The datetime the measurement is for (primary index)
    _datetime = DateTimeType(required = True)

    # _series = ModelType(FlightMeasurementSeriesIdentifier, required=True)

    measured_values = DictType(BaseType)

def getConcreteMeasuredValuesType(schemas: list[FlightMeasurementSchema]):

    res_types = dict()

    for schema in schemas:
        if schema.type == 'string':
            res_types[schema.name] = StringType()
        elif schema.type == 'int':
            res_types[schema.name] = IntType()
        elif schema.type == 'float':
            res_types[schema.name] = FloatType()
        else:
            raise NotImplementedError(f'Schema type {schema.type} not supported')
        
    return type(str(uuid.uuid4()).upper(), (Model, ), res_types)

def getConcreteMeasurementSchema(schema: list[FlightMeasurementSchema]):
    return type(str(uuid.uuid4()).upper(), (FlightMeasurement, ), dict( measured_values = ModelType(getConcreteMeasuredValuesType(schema)) ))
    


