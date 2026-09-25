import uuid

from sqlalchemy.orm import Session

from app.models.category import Category


def get_by_id(db: Session, category_id: uuid.UUID) -> Category | None:
    return db.query(Category).filter(Category.id == category_id).first()


def get_by_slug(db: Session, slug: str) -> Category | None:
    return db.query(Category).filter(Category.slug == slug).first()


def list_all(db: Session) -> list[Category]:
    return db.query(Category).order_by(Category.name.asc()).all()


def create(db: Session, *, name: str, slug: str, parent_id: uuid.UUID | None) -> Category:
    category = Category(name=name, slug=slug, parent_id=parent_id)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
