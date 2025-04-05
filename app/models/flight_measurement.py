import datetime
from typing import Optional, Tuple, Union
from uuid import UUID
from pydantic import BaseModel, Field

from app.helper.datetime_model import AwareDatetimeModel

NumericalMeasurementTypes = int | float | bool

MeasurementTypes = str | NumericalMeasurementTypes

class FlightMeasurementSeriesIdentifier(BaseModel):
    
    flight_id: UUID = Field(alias='_flight_id', alias_priority=1, default=None)

    vessel_part_id: UUID = Field(alias='_vessel_part_id', alias_priority=1, default=None)

class FlightMeasurementDescriptor(BaseModel):
    """
    Describes a field in the measured data
    """

    name: str

    type: str | list[tuple[str, str]]
    """The type of the that measurement. Can be a "string", "int" or a "float" """


class FlightMeasurement(BaseModel): 

    part_index: int

    m_index: int

    measurements: list[Tuple[float, list[MeasurementTypes]]] = Field(default_factory=list)

class FlightMeasurementAggregated(AwareDatetimeModel):

    p_index: int

    m_index: int

    part_id: UUID | None

    series_name: str | None

    measurements: list[Tuple[float, list[MeasurementTypes] | MeasurementTypes]] = Field(default_factory=list)

    start_time: datetime.datetime = Field(alias='_start_time', alias_priority=1, default=datetime.datetime.fromtimestamp(0)) 

    end_time: datetime.datetime = Field(alias='_end_time', alias_priority=1, default=datetime.datetime.fromtimestamp(0)) 

    min: list[NumericalMeasurementTypes] | NumericalMeasurementTypes | None

    avg: list[NumericalMeasurementTypes] | NumericalMeasurementTypes | None

    max: list[NumericalMeasurementTypes] | NumericalMeasurementTypes | None

    first: Tuple[float, list[MeasurementTypes] | MeasurementTypes] 

    last:  Tuple[float, list[MeasurementTypes] | MeasurementTypes]


class FlightMeasurementDB(AwareDatetimeModel):

    p_index: int

    m_index: int

    measurements: list[Tuple[float, list[MeasurementTypes] | MeasurementTypes]] = Field(default_factory=list)

    start_time: datetime.datetime = Field(alias='_start_time', alias_priority=1, default=datetime.datetime.fromtimestamp(0)) 

    end_time: datetime.datetime = Field(alias='_end_time', alias_priority=1, default=datetime.datetime.fromtimestamp(0)) 

    min: list[NumericalMeasurementTypes] | NumericalMeasurementTypes | None

    avg: list[NumericalMeasurementTypes] | NumericalMeasurementTypes | None

    max: list[NumericalMeasurementTypes] | NumericalMeasurementTypes | None

