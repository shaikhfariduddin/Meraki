"""
Seller onboarding business logic: apply, approve, reject, suspend.

The state machine is deliberately narrow:

  PENDING -> APPROVED
  PENDING -> REJECTED
  APPROVED -> SUSPENDED
  REJECTED -> PENDING   (reapplying overwrites the same row)

Anything else (approving a rejected application, suspending a pending
one, etc.) is an InvalidTransition — there is no endpoint that lets a
caller skip a state.
"""
from datetime import datetime, timezone

from app.models.seller_profile import SellerStatus
from app.models.user import UserRole
from app.repositories import seller_repository, user_repository


class AlreadyApplied(Exception):
    pass


class ApplicationNotFound(Exception):
    pass


class InvalidTransition(Exception):
    pass


def apply_for_seller(db, *, user, business_name: str):
    existing = seller_repository.get_by_user_id(db, user.id)

    if existing is None:
        return seller_repository.create(db, user_id=user.id, business_name=business_name)

    if existing.status in (SellerStatus.PENDING, SellerStatus.APPROVED):
        raise AlreadyApplied(existing.status)

    if existing.status == SellerStatus.SUSPENDED:
        raise InvalidTransition("Suspended sellers cannot reapply — contact an admin")

    # REJECTED — reuse the same row for a fresh application
    existing.business_name = business_name
    existing.status = SellerStatus.PENDING
    existing.reviewed_at = None
    existing.rejection_reason = None
    return seller_repository.save(db, existing)


def _get_or_404(db, seller_id):
    profile = seller_repository.get_by_id(db, seller_id)
    if profile is None:
        raise ApplicationNotFound(seller_id)
    return profile


def approve(db, *, seller_id):
    profile = _get_or_404(db, seller_id)
    if profile.status != SellerStatus.PENDING:
        raise InvalidTransition(f"Cannot approve from status '{profile.status.value}'")

    user = user_repository.get_by_id(db, profile.user_id)
    profile.status = SellerStatus.APPROVED
    profile.reviewed_at = datetime.now(timezone.utc)
    profile.rejection_reason = None
    user.role = UserRole.SELLER

    # Single commit — profile status and role flip together, or neither does.
    db.add(profile)
    db.add(user)
    db.commit()
    db.refresh(profile)
    return profile


def reject(db, *, seller_id, reason: str | None = None):
    profile = _get_or_404(db, seller_id)
    if profile.status != SellerStatus.PENDING:
        raise InvalidTransition(f"Cannot reject from status '{profile.status.value}'")
    profile.status = SellerStatus.REJECTED
    profile.reviewed_at = datetime.now(timezone.utc)
    profile.rejection_reason = reason
    return seller_repository.save(db, profile)


def suspend(db, *, seller_id, reason: str | None = None):
    profile = _get_or_404(db, seller_id)
    if profile.status != SellerStatus.APPROVED:
        raise InvalidTransition(f"Cannot suspend from status '{profile.status.value}'")
    profile.status = SellerStatus.SUSPENDED
    profile.reviewed_at = datetime.now(timezone.utc)
    profile.rejection_reason = reason
    return seller_repository.save(db, profile)
