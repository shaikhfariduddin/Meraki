"""
/api/products/* — public browsing, plus seller-owned creation and
management. Route order matters: /mine must be declared before
/{product_id} or FastAPI would try to parse "mine" as a UUID.
"""
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.seller import get_current_seller_profile
from app.models.seller_profile import SellerProfile
from app.repositories import product_repository
from app.schemas.product import (
    ProductCreate,
    ProductListOut,
    ProductOut,
    ProductSort,
    ProductUpdate,
    StockUpdate,
)
from app.services import product_service

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=ProductListOut)
def list_products(
    keyword: str | None = Query(default=None, max_length=255),
    category_id: uuid.UUID | None = Query(default=None),
    seller_id: uuid.UUID | None = Query(default=None),
    brand: str | None = Query(default=None, max_length=255),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    in_stock_only: bool = Query(default=False),
    sort: ProductSort = Query(default=ProductSort.NEWEST),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    try:
        items, total = product_service.search_products(
            db,
            keyword=keyword,
            category_id=category_id,
            seller_id=seller_id,
            brand=brand,
            min_price=min_price,
            max_price=max_price,
            in_stock_only=in_stock_only,
            sort=sort.value,
            page=page,
            page_size=page_size,
        )
    except product_service.InvalidPriceRange:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="min_price cannot exceed max_price"
        )
    return ProductListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/mine", response_model=list[ProductOut])
def list_my_products(
    seller_profile: SellerProfile = Depends(get_current_seller_profile),
    db: Session = Depends(get_db),
):
    return product_repository.list_by_seller(db, seller_profile.id)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)):
    product = product_repository.get_by_id(db, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    seller_profile: SellerProfile = Depends(get_current_seller_profile),
    db: Session = Depends(get_db),
):
    try:
        return product_service.create_product(db, seller_profile=seller_profile, payload=payload)
    except product_service.CategoryNotFound:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="category_id does not exist"
        )


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    seller_profile: SellerProfile = Depends(get_current_seller_profile),
    db: Session = Depends(get_db),
):
    try:
        return product_service.update_product(
            db, seller_profile=seller_profile, product_id=product_id, payload=payload
        )
    except product_service.ProductNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    except product_service.NotProductOwner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this product"
        )
    except product_service.CategoryNotFound:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="category_id does not exist"
        )


@router.post("/{product_id}/deactivate", response_model=ProductOut)
def deactivate_product(
    product_id: uuid.UUID,
    seller_profile: SellerProfile = Depends(get_current_seller_profile),
    db: Session = Depends(get_db),
):
    try:
        return product_service.deactivate_product(
            db, seller_profile=seller_profile, product_id=product_id
        )
    except product_service.ProductNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    except product_service.NotProductOwner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this product"
        )


@router.patch("/{product_id}/stock", response_model=ProductOut)
def update_stock(
    product_id: uuid.UUID,
    payload: StockUpdate,
    seller_profile: SellerProfile = Depends(get_current_seller_profile),
    db: Session = Depends(get_db),
):
    try:
        return product_service.update_stock(
            db,
            seller_profile=seller_profile,
            product_id=product_id,
            available_stock=payload.available_stock,
        )
    except product_service.ProductNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    except product_service.NotProductOwner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this product"
        )
