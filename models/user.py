from dataclasses import dataclass, field
from datetime import datetime, timedelta
from datetime import timezone
from typing import Union
from uuid import UUID, uuid4
from marshmallow import Schema, fields
from models.command import CommandInfo, CommandInfoSchema
from models.flight_measurement import FlightMeasurement, FlightMeasurementDescriptor, FlightMeasurementDescriptorSchema
from models.vessel import VesselSchema
from helper.model_helper import make_safe_schema
from hashlib import sha256
import base64

def hash_password(user_id: UUID, pw: str):
    as_bytes = (pw + str(user_id)).encode()
    return base64.b64encode(sha256(as_bytes).digest()).decode('utf-8')

@dataclass
class User:

    _id: UUID

    pw: Union[str, None]
    ''' Password or access token (salted and hashed) '''

    unique_name: str = ""
    '''unique name of the user (e.g. an email address)'''

    name: str = ""

    roles: list[str] = field(default_factory=list)


class UserSchema(make_safe_schema(User)):

    _id = fields.UUID()

    unique_name = fields.String(required=True)
    '''unique name of the user (e.g. an email address)'''

    name = fields.String()

    pw = fields.String(allow_none=True)
    ''' Password or access token (salted and hashed) '''

    roles = fields.List(fields.String())
