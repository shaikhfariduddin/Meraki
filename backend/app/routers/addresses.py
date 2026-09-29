import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.address import AddressCreate, AddressOut, AddressUpdate
from app.services import address_service

router = APIRouter(prefix="/api/addresses", tags=["addresses"])


@router.get("", response_model=list[AddressOut])
def list_addresses(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return address_service.list_addresses(db, user=current_user)


@router.post("", response_model=AddressOut, status_code=status.HTTP_201_CREATED)
def create_address(
    payload: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return address_service.create_address(db, user=current_user, payload=payload)


@router.patch("/{address_id}", response_model=AddressOut)
def update_address(
    address_id: uuid.UUID,
    payload: AddressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return address_service.update_address(
            db, user=current_user, address_id=address_id, payload=payload
        )
    except address_service.AddressNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    address_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        address_service.delete_address(db, user=current_user, address_id=address_id)
    except address_service.AddressNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
