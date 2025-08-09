import asyncio
from typing import List
from uuid import UUID

from app.services.data_access.flight import bulk_delete_flights_by_ids
from app.services.data_access.flight_data import bulk_delete_flight_commands_by_flight_ids, bulk_delete_flight_data_by_flight_ids


class FlightService:
    @staticmethod
    async def bulk_delete_flights_by_ids(_ids: List[UUID]) -> bool:
        results = await asyncio.gather(
            bulk_delete_flight_data_by_flight_ids(_ids),
            bulk_delete_flight_commands_by_flight_ids(_ids),
            bulk_delete_flights_by_ids(_ids)
        )

        return results[2]