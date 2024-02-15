from typing import Union
from uuid import UUID
from pydantic import BaseModel, Field

class VesselPart(BaseModel):
    
    id: UUID = Field(alias='_id',  alias_priority=1, default=None)
    """
    ID of the part. Primary identifier
    """

    name: str = ""

    part_type: str = ""
    """
    The type of the part. This is supposed to be used as a quick identifier
    to group the parts or to visualize them. This shouldn't be used to
    describe the capabilities of the part
    """

    virtual: bool = False
    """
    Whether or not the component actually exist extend physically
    or if it is just a virtual capability of the vessel
    """

    parent: Union[UUID, None] = None
    """
    The _id of the parent of this part
    """


