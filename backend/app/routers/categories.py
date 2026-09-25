from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_role
from app.models.user import UserRole
from app.repositories import category_repository
from app.schemas.category import CategoryCreate, CategoryOut

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return category_repository.list_all(db)


@router.post(
    "",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    if category_repository.get_by_slug(db, payload.slug) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
    if payload.parent_id is not None and category_repository.get_by_id(db, payload.parent_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="parent_id does not exist")
    return category_repository.create(
        db, name=payload.name, slug=payload.slug, parent_id=payload.parent_id
    )
