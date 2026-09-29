import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

_PHONE_RE = re.compile(r"^[+\d][\d\s\-()]{6,19}$")


def _validate_phone(v: str | None) -> str | None:
    if v is not None and not _PHONE_RE.match(v):
        raise ValueError("Not a valid phone number")
    return v


class AddressCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=1, max_length=32)
    address_line: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=255)
    state: str = Field(min_length=1, max_length=255)
    postal_code: str = Field(min_length=1, max_length=32)
    country: str = Field(min_length=1, max_length=255)

    _check_phone = field_validator("phone")(_validate_phone)


class AddressUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, min_length=1, max_length=32)
    address_line: str | None = Field(default=None, min_length=1, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=255)
    state: str | None = Field(default=None, min_length=1, max_length=255)
    postal_code: str | None = Field(default=None, min_length=1, max_length=32)
    country: str | None = Field(default=None, min_length=1, max_length=255)

    _check_phone = field_validator("phone")(_validate_phone)


class AddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    phone: str
    address_line: str
    city: str
    state: str
    postal_code: str
    country: str
