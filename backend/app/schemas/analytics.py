from decimal import Decimal

from pydantic import BaseModel


class AdminAnalyticsOut(BaseModel):
    total_users: int
    total_sellers: int
    total_products: int
    total_orders: int
    total_revenue: Decimal
    pending_orders: int
    low_stock_products: int


class SellerAnalyticsOut(BaseModel):
    total_products: int
    active_products: int
    total_orders: int
    total_revenue: Decimal
    low_stock_products: int
