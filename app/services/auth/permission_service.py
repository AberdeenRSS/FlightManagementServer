

from typing import Union
from uuid import UUID
from ...models.flight import Flight
from app.models.vessel import Vessel
from app.services.auth.jwt_user_info import UserInfo, get_socket_user_info

permission_index = {
    'none': 0,
    'view': 1,
    'read': 2,
    'write': 3,
    'owner': 4
}

def get_permission_index(permission_name: str) -> int:

    if permission_name not in permission_index:
        return 0
    
    return permission_index[permission_name]

def has_vessel_permission(vessel: Vessel, permission: str, user: UserInfo):
    ''' Returns wether the current user has permission to access the vessel on the requested permission level'''

    if user is None:
        return 0
    
    
    no_auth_permission = get_permission_index(vessel.no_auth_permission or 'none')

    user_permission = 0

    if user is not None:
        if user._id in vessel.permissions:
            user_permission = get_permission_index(vessel.permissions[user._id])

    return max(no_auth_permission, user_permission) >= get_permission_index(permission)

def has_flight_permission(flight: Flight, vessel: Vessel, permission: str, user: UserInfo):
    '''
    Returns wether the current user has  permission to access the flight on the requested permission level.
    If there are no flight permissions the vessel permission is used
    '''

    no_auth_permission = get_permission_index(flight.no_auth_permission or 'none')

    user_permission = 0

    if user is not None:
        if user._id in flight.permissions:
            user_permission = get_permission_index(flight.permissions[user._id])

    if max(no_auth_permission, user_permission) >= get_permission_index(permission):
        return True
    
    return has_vessel_permission(vessel, permission, user)

def make_everyone_owner_if_no_owner(vessel: Vessel):

    owner = False
    for p in vessel.permissions.values():
        if p == 'owner':
            owner = True
    
    if owner:
        return
    
    vessel.no_auth_permission = 'owner'


def modify_vessel_permission(vessel: Vessel, permission: str, user_id: UUID):

    if permission == 'none':
        del vessel.permissions[str(user_id)]
    else:
        vessel.permissions[str(user_id)] = permission

    make_everyone_owner_if_no_owner(vessel)

def modify_flight_permission(flight: Flight, permission: str, user_id: UUID):

    if permission == 'none':
        del flight.permissions[str(user_id)]
    else:
        flight.permissions[str(user_id)] = permission