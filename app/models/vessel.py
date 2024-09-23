from typing import Any, TypeVar, Union, cast
from uuid import UUID
from pydantic import BaseModel, Field

from ..models.vessel_part import VesselPart

class Vessel(BaseModel):
    
    id: UUID = Field(alias='_id', alias_priority=1, default=None)
    """
    The id of the vessel (primary identifier)
    """

    version: int = Field(alias='_version', alias_priority=1, default=0)
    """
    The version of this vessel
    This is to track if any of the information about the vessel
    changes. Old versions of the vessel can still be accessed
    to allow old flights to still be valid
    """

    name: str = ''
    """
    Name of the vessel
    """

    parts: list[VesselPart] = Field(default_factory=list)
    """
    All the parts (components) of the vessel
    """

    permissions: dict[str, str] = Field(default_factory=dict)
    """
    User id permission pairs of who has what permission on the vessel
    """

    no_auth_permission: Union[None, str] = 'owner'
    """
    The permission everyone has regardless of if they are logged in or not
    """

class VesselHistoricKey(BaseModel):
    version: int

    id: UUID

class VesselHistoric(BaseModel):
    
    id: VesselHistoricKey = Field(..., alias='_id')
    """
    The id of the vessel (primary identifier)
    """

    _version: int = 0
    """
    The version of this vessel
    This is to track if any of the information about the vessel
    changes. Old versions of the vessel can still be accessed
    to allow old flights to still be valid
    """

    name: str = ''
    """
    Name of the vessel
    """

    parts: list[VesselPart] = Field(default_factory=list)
    """
    All the parts (components) of the vessel
    """

