import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.seller_profile import SellerStatus


class SellerApplicationCreate(BaseModel):
    business_name: str = Field(min_length=1, max_length=255)


class SellerReviewRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class SellerProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    business_name: str
    status: SellerStatus
    created_at: datetime
    reviewed_at: datetime | None
    rejection_reason: str | None
