
from schematics.models import Model
from schematics.types import StringType, UUIDType, ListType, ModelType, IntType

from models.vessel_part import VesselPart

class Vessel(Model):
    # The id of the vessel
    _id = UUIDType(required=True)

    # The version of this vessel
    # This is to track if any of the information about the vessel
    # changes. Old versions of the vessel can still be accessed
    # to allow old flights to still be valid
    _version = IntType(required=False)

    # The name of the vessel
    name = StringType(required=True)

    # All parts of this vessel
    parts = ListType(ModelType(VesselPart), default=[])


