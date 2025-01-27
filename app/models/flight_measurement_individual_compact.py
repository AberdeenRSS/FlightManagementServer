import datetime
from typing import Tuple, Union
from uuid import UUID
from pydantic import BaseModel, Field

from app.helper.datetime_model import AwareDatetimeModel

MeasurementTypes = str | int | float

class FlightMeasurementIndividualCompact(BaseModel): 

    part_index: int

    m_index: int

    measurements: list[Tuple[float, list[MeasurementTypes]]] = Field(default_factory=list)


class FlightMeasurementIndividualCompactDB(AwareDatetimeModel):

    p_index: int

    m_index: int

    measurements: list[Tuple[float, list[MeasurementTypes] | MeasurementTypes]] = Field(default_factory=list)

    start_time: datetime.datetime = Field(alias='_start_time', alias_priority=1, default=datetime.datetime.fromtimestamp(0)) 

    end_time: datetime.datetime = Field(alias='_end_time', alias_priority=1, default=datetime.datetime.fromtimestamp(0)) 

    measurements_aggregated: tuple[MeasurementTypes, MeasurementTypes, MeasurementTypes] = Field(default_factory=tuple)

