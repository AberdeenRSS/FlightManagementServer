from dataclasses import dataclass, field
from typing import Any, TypeVar, Union, cast
from uuid import UUID
from marshmallow import Schema, fields, post_load, validate
from helper.model_helper import SchemaExt, make_safe_schema

from models.vessel_part import VesselPart, VesselPartSchema

@dataclass
class Vessel:
    
    _id: UUID
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

    parts: list[VesselPart] = field(default_factory=list)
    """
    All the parts (components) of the vessel
    """

    permissions: dict[UUID, str] = field(default_factory=dict)
    """
    User id permission pairs of who has what permission on the vessel
    """

    no_auth_permission: Union[None, str] = 'owner'
    """
    The permission everyone has regardless of if they are logged in or not
    """

class VesselSchema(make_safe_schema(Vessel)):

    _id = fields.UUID(required=True)
    """
    The id of the vessel (primary identifier)
    """

    _version = fields.Int(required=False)
    """
    The version of this vessel
    This is to track if any of the information about the vessel
    changes. Old versions of the vessel can still be accessed
    to allow old flights to still be valid
    """

    name = fields.String(required=True)
    """
    Name of the vessel
    """

    parts = fields.List(fields.Nested(VesselPartSchema), load_default=[], dump_default=[])
    """
    All the parts (components) of the vessel. The parts have hierarchy by linking between each other
    """

    permissions = fields.Dict(fields.UUID, fields.String(validate=validate.Regexp(r"(view)|(read)|(write)|(owner)")))
    """
    User id permission pairs of who has what permission on the vessel
    """

    no_auth_permission = fields.String(default='owner', missing='owner', validate=validate.Regexp(r"(none)|(view)|(read)|(write)|(owner)"))
    """
    The permission everyone has regardless of if they are logged in or not
    """

@dataclass
class VesselHistoricKey:
    version: int

    id: UUID

@dataclass
class VesselHistoric:
    
    _id: VesselHistoricKey
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

    parts: list[VesselPart] = field(default_factory=list)
    """
    All the parts (components) of the vessel
    """

class VesselHistoricKeySchema(make_safe_schema(VesselHistoricKey)):
    version = fields.Integer(required=True)

    id = fields.UUID(required=True)


class VesselHistoricSchema(make_safe_schema(VesselHistoric)):

    _id = fields.Nested(VesselHistoricKeySchema)
    """
    The id of the vessel (primary identifier)
    """

    _version = fields.Int(required=False)
    """
    The version of this vessel
    This is to track if any of the information about the vessel
    changes. Old versions of the vessel can still be accessed
    to allow old flights to still be valid
    """

    name = fields.String(required=True)
    """
    Name of the vessel
    """

    parts = fields.List(fields.Nested(VesselPartSchema), load_default=[], dump_default=[])
    """
    All the parts (components) of the vessel. The parts have hierarchy by linking between each other
    """


