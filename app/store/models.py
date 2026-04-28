from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.store.database import Base


class Product(Base):
    __tablename__ = "products"

    sku_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    current_price: Mapped[float] = mapped_column(Float, nullable=False)
    promo_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stock_num: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    specs_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_on_sale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    promotions: Mapped[list["Promotion"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class Promotion(Base):
    __tablename__ = "promotions"

    promo_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("products.sku_id"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    discount_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    start_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    product: Mapped[Product] = relationship(back_populates="promotions")


class EcommerceLogistics(Base):
    __tablename__ = "ecommerce_logistics"

    order_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    sku_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    carrier: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class RepairTicket(Base):
    __tablename__ = "repair_tickets"

    ticket_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    product: Mapped[str] = mapped_column(String(255), nullable=False)
    issue: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    estimated_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)


class TrackingOrder(Base):
    __tablename__ = "tracking_orders"

    order_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tracking_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    carrier: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    items: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    events: Mapped[list["TrackingEvent"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="TrackingEvent.event_time",
    )


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("tracking_orders.order_id"), nullable=False, index=True)
    event_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    event_text: Mapped[str] = mapped_column("event", String(255), nullable=False)

    order: Mapped[TrackingOrder] = relationship(back_populates="events")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class FeedbackRecord(Base):
    __tablename__ = "feedback_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    resolved: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
