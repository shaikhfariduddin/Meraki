import uuid

from sqlalchemy.orm import Session

from app.models.seller_profile import SellerProfile, SellerStatus


def get_by_user_id(db: Session, user_id: uuid.UUID) -> SellerProfile | None:
    return db.query(SellerProfile).filter(SellerProfile.user_id == user_id).first()


def get_by_id(db: Session, seller_id: uuid.UUID) -> SellerProfile | None:
    return db.query(SellerProfile).filter(SellerProfile.id == seller_id).first()


def list_by_status(db: Session, status: SellerStatus | None) -> list[SellerProfile]:
    query = db.query(SellerProfile)
    if status is not None:
        query = query.filter(SellerProfile.status == status)
    return query.order_by(SellerProfile.created_at.asc()).all()


def create(db: Session, *, user_id: uuid.UUID, business_name: str) -> SellerProfile:
    profile = SellerProfile(user_id=user_id, business_name=business_name)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def save(db: Session, profile: SellerProfile) -> SellerProfile:
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile
