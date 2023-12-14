from datetime import UTC, datetime
from pydantic import BaseModel


class AwareDatetimeModel(BaseModel):
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
        }

    @classmethod
    def datetime_utc(cls, dt: datetime) -> datetime:
        return dt.astimezone(UTC)

    @classmethod
    def parse_datetime(cls, value):
        if value and isinstance(value, str):
            return cls.datetime_utc(datetime.fromisoformat(value))
        return value