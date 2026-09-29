import uuid

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.product import Inventory


def decrement_stock(db: Session, product_id: uuid.UUID, quantity: int) -> int:
    """
    Atomically take `quantity` units out of stock. Returns the number of rows
    updated: 1 on success, 0 if there wasn't enough stock.

    This is a single conditional UPDATE — the "is there enough?" check and the
    subtraction happen in one statement, inside the database. The naive
    version (SELECT stock; check in Python; UPDATE stock = stock - n) lets two
    concurrent buyers both read "2 in stock" and both succeed. Here the second
    UPDATE re-evaluates the WHERE clause against the first one's result (row
    locks in PostgreSQL make it wait for the first to finish), matches zero
    rows, and the caller knows to abort.

    The caller owns the transaction; nothing is committed here.
    """
    result = db.execute(
        update(Inventory)
        .where(Inventory.product_id == product_id, Inventory.available_stock >= quantity)
        .values(available_stock=Inventory.available_stock - quantity)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount


def increment_stock(db: Session, product_id: uuid.UUID, quantity: int) -> None:
    """
    Return `quantity` units to stock — used when a seller cancels an
    order. No conditional WHERE needed here (unlike decrement_stock):
    adding stock back can't oversell anything, so there's no race to
    guard against.
    """
    db.execute(
        update(Inventory)
        .where(Inventory.product_id == product_id)
        .values(available_stock=Inventory.available_stock + quantity)
        .execution_options(synchronize_session=False)
    )
