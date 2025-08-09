import asyncio
from typing import List
from uuid import UUID

from app.services.data_access.flight import bulk_delete_flights_by_ids, get_all_flights_for_vessels
from app.services.data_access.flight_data import bulk_delete_flight_commands_by_flight_ids, bulk_delete_flight_data_by_flight_ids
from app.services.data_access.vessel import delete_vessel_by_id
from app.services.flight_service import FlightService


class VesselService:
    @staticmethod
    async def delete_vessel(_id: UUID) -> bool:
        flights = await get_all_flights_for_vessels(_id)
        flight_ids = [flight.id for flight in flights]

        results = await asyncio.gather(
            FlightService.bulk_delete_flights_by_ids(flight_ids),
            delete_vessel_by_id(_id),
        )

        return results[1]
        