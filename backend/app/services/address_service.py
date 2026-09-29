"""
Address business logic. Ownership is enforced here — get_for_user
already filters by user_id, so "not found" and "not yours" are
indistinguishable by design (same pattern as cart items and orders).
"""
from app.repositories import address_repository


class AddressNotFound(Exception):
    pass


def list_addresses(db, *, user):
    return address_repository.list_for_user(db, user.id)


def create_address(db, *, user, payload):
    return address_repository.create(db, user_id=user.id, **payload.model_dump())


def update_address(db, *, user, address_id, payload):
    address = address_repository.get_for_user(db, user.id, address_id)
    if address is None:
        raise AddressNotFound()

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(address, field, value)
    return address_repository.save(db, address)


def delete_address(db, *, user, address_id):
    address = address_repository.get_for_user(db, user.id, address_id)
    if address is None:
        raise AddressNotFound()
    address_repository.delete(db, address)
