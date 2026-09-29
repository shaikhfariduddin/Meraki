from app.repositories import order_repository


class OrderNotFound(Exception):
    pass


def get_order(db, *, user, order_id):
    order = order_repository.get_for_user(db, user.id, order_id)
    if order is None:
        # Same answer for "doesn't exist" and "belongs to someone else", so
        # the API never confirms another customer's order id is real.
        raise OrderNotFound()
    return order


def list_orders(db, *, user, page: int, page_size: int):
    return order_repository.list_for_user(db, user.id, page=page, page_size=page_size)
