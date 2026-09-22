"""
Auth business logic: registration and login.

Routers call these functions and translate the results (or exceptions)
into HTTP responses — the service layer itself knows nothing about
FastAPI or HTTP status codes.
"""
from app.repositories import user_repository
from app.utils.security import create_access_token, hash_password, verify_password


class EmailAlreadyRegistered(Exception):
    pass


class InvalidCredentials(Exception):
    pass


def register_user(db, *, email: str, password: str, full_name: str):
    if user_repository.get_by_email(db, email):
        raise EmailAlreadyRegistered(email)
    user = user_repository.create(
        db, email=email, password_hash=hash_password(password), full_name=full_name
    )
    return user


def authenticate_user(db, *, email: str, password: str):
    user = user_repository.get_by_email(db, email)
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise InvalidCredentials()
    return user


def issue_token_for(user) -> str:
    return create_access_token(subject=str(user.id), role=user.role.value)
