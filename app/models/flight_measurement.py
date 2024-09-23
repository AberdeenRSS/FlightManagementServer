from datetime import datetime, timezone
from typing import Type, Union
import uuid
from pydantic import BaseModel, Field, create_model

from app.helper.datetime_model import AwareDatetimeModel

class FlightMeasurementSeriesIdentifier(BaseModel):
    
    flight_id: uuid.UUID = Field(alias='_flight_id', alias_priority=1, default=None)

    vessel_part_id: uuid.UUID = Field(alias='_vessel_part_id', alias_priority=1, default=None)

class FlightMeasurementDescriptor(BaseModel):
    """
    Describes a field in the measured data
    """

    name: str

    type: str
    """The type of the that measurement. Can be a "string", "int" or a "float" """

class FlightMeasurement(AwareDatetimeModel):
    """A single measurement relayed back by the model
    """
    
    datetime_value: Union[datetime, None] = Field(alias='_datetime', alias_priority=1, default=None)
    """The datetime the measurement is for (primary index)"""

    measured_values: dict[str, Union[str, int, float]] = Field(default_factory=dict)
    """The measured values themselves"""

    id: Union[uuid.UUID, None] = Field(alias='_id', alias_priority=1, default=None)

    part_id: Union[uuid.UUID, None] = None
    """Optional part id. Used to send the part over the network, not committed to database"""

def getConcreteMeasuredValuesType(schemas: list[FlightMeasurementDescriptor]):
    """
    Creates a new marshmallow definition according to the past schemas.
    This definition will have the measurement name as the property key
    and the value as the passed type
    """

    res_types = dict()

    for schema in schemas:
        if schema.type == 'string':
            res_types[schema.name] = (str, ...)
        elif schema.type == 'int':
            res_types[schema.name] = (int, ...)
        elif schema.type == 'float':
            res_types[schema.name] = (float, ...)
        else:
            raise NotImplementedError(f'Schema type {schema.type} not supported')
        
    return create_model(str(uuid.uuid4()).upper(), **res_types)
        

def getConcreteMeasurementSchema(schema: list[FlightMeasurementDescriptor]) -> Type[FlightMeasurement]:
    """
    Creates a new FlightMeasurement schema based on the requested properties.
    Replaces the `FlightMeasurement.measured_values` with a nested schema
    which has the correct keys and value types for validation
    """

    measurement_model = getConcreteMeasuredValuesType(schema)

    return create_model(str(uuid.uuid4()).upper(), __base__ = FlightMeasurement, measured_values=(measurement_model, ...))
