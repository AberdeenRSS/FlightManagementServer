from dataclasses import dataclass
from typing import Union
from uuid import UUID
from marshmallow import Schema, fields
from helper.model_helper import make_safe_schema

@dataclass
class VesselPart:
    _id: UUID
    """
    ID of the part. Primary identifier
    """

    name = ""

    part_type = ""
    """
    The type of the part. This is supposed to be used as a quick identifier
    to group the parts or to visualize them. This shouldn't be used to
    describe the capabilities of the part
    """

    virtual = False
    """
    Whether or not the component actually exist extend physically
    or if it is just a virtual capability of the vessel
    """

    parent: Union[UUID, None] = None
    """
    The _id of the parent of this part
    """

# A vessel part is a sub component of a vessel that full fills a certain task
# This class describes a vessel 
class VesselPartSchema(make_safe_schema(VesselPart)):

    _id = fields.UUID(required=True)
    """
    ID of the part. Primary identifier
    """

    name = fields.String(required=False)

    part_type = fields.String(required=True)
    """
    The type of the part. This is supposed to be used as a quick identifier
    to group the parts or to visualize them. This shouldn't be used to
    describe the capabilities of the part
    """

    virtual = fields.Boolean(load_default=False, dump_default=False, required=False)
    """
    Whether or not the component actually exist extend physically
    or if it is just a virtual capability of the vessel
    """

    parent = fields.UUID(required=False)
    """
    The _id of the parent of this part
    """
