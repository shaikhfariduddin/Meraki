"""
/api/auth/* — registration, login, and "who am I".
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import Token, UserCreate, UserOut
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        user = auth_service.register_user(
            db, email=payload.email, password=payload.password, full_name=payload.full_name
        )
    except auth_service.EmailAlreadyRegistered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email is already registered"
        )
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm uses "username" for the identifier field;
    # we treat that field as the email.
    try:
        user = auth_service.authenticate_user(
            db, email=form_data.username, password=form_data.password
        )
    except auth_service.InvalidCredentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_service.issue_token_for(user)
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
