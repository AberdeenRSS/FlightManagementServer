from typing import Annotated, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from uuid import UUID, uuid4
from datetime import datetime, timezone, UTC
from app.middleware.auth.requireAuth import AuthOptional, AuthRequired, user_optional, user_required, verify_role
from app.models.flight import Flight, FLIGHT_DEFAULT_HEAD_TIME
from app.services.auth.jwt_user_info import UserInfo, get_socket_user_info
from app.services.auth.permission_service import has_flight_permission, modify_flight_permission
from app.services.data_access.flight import create_or_update_flight, get_all_flights_for_vessels, get_all_flights_for_vessels_by_name, get_flight
from app.services.data_access.user import get_user_by_unique_name
from app.services.data_access.vessel import get_vessel 
from app.controller.vessel_controller import vessels_controller
from app.models.permissions import Permission


flight_controller = APIRouter(
    prefix="/flight",
    tags=["flight"],
    dependencies=[],
)

flights_controller = APIRouter(
    prefix="/v1/flights",
    tags=["v1/flights"],
    dependencies=[],
)

# Method for a vessel to register
@flights_controller.post("/")
@flight_controller.post("/create")
async def create_flight(flight: Flight, user: AuthRequired) -> Flight:
    """
    Creates a flight
    """

    verify_role(user, 'vessel')

    # Create a new random uuid for the flight
    flight._id = uuid4()

    flight.start = datetime.now(UTC)

    # flight.start = flight.start.replace(tzinfo=timezone.utc)

    flight.end = datetime.now(UTC) + FLIGHT_DEFAULT_HEAD_TIME

    # flight.end = flight.end.replace(tzinfo=timezone.utc)

    # Load the vessel to ensure it exists and to get its current version
    vessel = await get_vessel(flight.vessel_id)

    if vessel is None:
        raise HTTPException(400, f'Vessel {flight.vessel_id} does not exist yet. Please create the vessel before creating a flight for it')
        
    flight.vessel_version = vessel.version

    acc = await create_or_update_flight(flight)

    return acc


@flight_controller.get("/get_all/{vessel_id}")
async def get_all_legacy(vessel_id:UUID,user:AuthOptional) -> list[Flight]:
    """
    Fetches all flights that the passed vessel ever performed
    """
    return await get_all(vessel_id, user)


@vessels_controller.get("/{vessel_id}/flights",tags=["v1/flights"])
async def get_all(vessel_id: UUID, user: AuthOptional, name: Optional[str] = Query(default=None, description="Filter flights by name")) -> list[Flight]:
    """
    Fetches all flights that the passed vessel ever performed
    """

    vessel = await get_vessel(vessel_id)

    if vessel is None:
        raise HTTPException(400, 'Vessel does not exist')

    flights = await get_all_flights_for_vessels(vessel_id)

    flights = [f for f in flights if has_flight_permission(f, vessel, 'view', user)]

    if name is not None:
        name = str(name).lower()
        flights = [f for f in flights if name in f.name.lower()]
    return flights


@flight_controller.get("/get_by_name/{vessel_id}/{name}")
async def get_by_name(vessel_id: UUID, name: str, user: AuthOptional) -> list[Flight]:
    '''
    Fetches all flights with the specified name
    '''

    vessel = await get_vessel(vessel_id)

    if vessel is None:
        raise HTTPException(400, 'Vessel does not exist')
    
    flights = await get_all_flights_for_vessels_by_name(vessel_id, name)
    return [f for f in flights if has_flight_permission(f, vessel, 'view', user)]

@flight_controller.post('/set_permission/{flight_id}/{unique_user_name}/{permission}')
async def set_permission_legacy(flight_id:UUID,unique_user_name:str,permission:str,user:AuthOptional):
    permission_data = Permission(
        unique_user_name=unique_user_name,
        permission=permission
    )
    return await set_permission(user,flight_id,permission_data)

@flights_controller.post("/flights/{flight_id}/permissions")
async def set_permission(user: AuthOptional, flight_id: UUID, permission_data: Permission=Body()):

    flight = await get_flight(flight_id)

    if flight is None:
        raise HTTPException(404, 'Flight does not exist')
    
    vessel = await get_vessel(flight.vessel_id)

    if vessel is None:
        raise HTTPException(404, 'Vessel does not exist')
    
    if not has_flight_permission(flight, vessel, 'owner', user):
        raise HTTPException(403, 'You don\'t have the required permission to access the flight')
    
    unique_user_name = permission_data.unique_user_name
    permission = permission_data.permission

    other_user = await get_user_by_unique_name(unique_user_name)

    if other_user is None:
        raise HTTPException(404, 'User you are trying to give permission to does not exist')
    
    modify_flight_permission(flight, permission, other_user.id)

    await create_or_update_flight(flight)

    return 'success'