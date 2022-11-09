from schematics.models import Model
from schematics.types import StringType, UUIDType, ListType, ModelType, BooleanType

# A vessel part is a sub component of a vessel that full fills a certain task
# This class describes a vessel 
class VesselPart(Model):

    # The id of the Vessel part
    _id = UUIDType(required=True)

    # The name of the part
    name = StringType(required=False)

    # The type of the part. This is supposed to be used as a quick identifier
    # to group the parts or to visualize them. This shouldn't be used to
    # describe the capabilities of the part
    part_type = StringType(required=True)

    # Whether or not the component actually exist extend physically
    # or if it is just a virtual capability of the vessel
    virtual = BooleanType(default=False, required=False)

    # The _id of the child parts this part has
    parent = UUIDType(required=False)


