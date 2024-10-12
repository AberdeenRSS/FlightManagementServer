from datetime import datetime, timezone
from pydantic import BaseModel

class AwareDatetimeModel(BaseModel):
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat() if dt is not None else "",
        }

    @classmethod
    def datetime_utc(cls, dt: datetime) -> datetime:
        return dt.astimezone(timezone.utc)

    @classmethod
    def parse_datetime(cls, value):
        if value and isinstance(value, str):
            return cls.datetime_utc(datetime.fromisoformat(value))
        return value