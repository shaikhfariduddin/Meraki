"""
User data access. Knows how to fetch/save User rows — nothing about
passwords, tokens, or business rules lives here.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.user import User


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_by_id(db: Session, user_id) -> User | None:
    """
    Accepts either a uuid.UUID or its string form — callers like
    get_current_user pass the JWT's `sub` claim, which is always a
    string, since JSON has no native UUID type. SQLAlchemy's Uuid
    column type expects an actual uuid.UUID on the Python side, so we
    convert here rather than pushing that concern onto every caller.
    """
    if not isinstance(user_id, uuid.UUID):
        try:
            user_id = uuid.UUID(str(user_id))
        except (ValueError, AttributeError, TypeError):
            return None
    return db.query(User).filter(User.id == user_id).first()


def create(db: Session, *, email: str, password_hash: str, full_name: str) -> User:
    user = User(email=email, password_hash=password_hash, full_name=full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
