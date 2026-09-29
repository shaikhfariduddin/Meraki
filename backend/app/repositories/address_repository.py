import uuid

from sqlalchemy.orm import Session

from app.models.address import Address


def list_for_user(db: Session, user_id: uuid.UUID) -> list[Address]:
    return (
        db.query(Address)
        .filter(Address.user_id == user_id)
        .order_by(Address.created_at.desc())
        .all()
    )


def get_for_user(db: Session, user_id: uuid.UUID, address_id: uuid.UUID) -> Address | None:
    return (
        db.query(Address)
        .filter(Address.id == address_id, Address.user_id == user_id)
        .first()
    )


def create(db: Session, *, user_id: uuid.UUID, **fields) -> Address:
    address = Address(user_id=user_id, **fields)
    db.add(address)
    db.commit()
    db.refresh(address)
    return address


def save(db: Session, address: Address) -> Address:
    db.add(address)
    db.commit()
    db.refresh(address)
    return address


def delete(db: Session, address: Address) -> None:
    db.delete(address)
    db.commit()
