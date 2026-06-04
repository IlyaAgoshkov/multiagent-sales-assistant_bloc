from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric,
    String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.db import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_info: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    source_channel: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    appeals: Mapped[list["Appeal"]] = relationship(back_populates="client")


class Manager(Base):
    __tablename__ = "managers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="manager")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    appeals: Mapped[list["Appeal"]] = relationship(back_populates="assigned_manager")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="manager")
    analytics: Mapped[list["Analytics"]] = relationship(back_populates="manager")


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Appeal(Base):
    __tablename__ = "appeals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    assigned_manager_id: Mapped[Optional[int]] = mapped_column(ForeignKey("managers.id"))
    source_channel: Mapped[Optional[str]] = mapped_column(String(100))

    client: Mapped["Client"] = relationship(back_populates="appeals")
    assigned_manager: Mapped[Optional["Manager"]] = relationship(back_populates="appeals")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="appeal")
    commercial_offers: Mapped[list["CommercialOffer"]] = relationship(back_populates="appeal")
    deals: Mapped[list["Deal"]] = relationship(back_populates="appeal")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appeal_id: Mapped[int] = mapped_column(ForeignKey("appeals.id"), nullable=False)
    manager_id: Mapped[int] = mapped_column(ForeignKey("managers.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    appeal: Mapped["Appeal"] = relationship(back_populates="recommendations")
    manager: Mapped["Manager"] = relationship(back_populates="recommendations")


class CommercialOffer(Base):
    __tablename__ = "commercial_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appeal_id: Mapped[int] = mapped_column(ForeignKey("appeals.id"), nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    appeal: Mapped["Appeal"] = relationship(back_populates="commercial_offers")


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appeal_id: Mapped[int] = mapped_column(ForeignKey("appeals.id"), nullable=False)
    probability: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    expected_close_at: Mapped[Optional[date]] = mapped_column(Date)
    actual_close_at: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    appeal: Mapped["Appeal"] = relationship(back_populates="deals")


class Analytics(Base):
    __tablename__ = "analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manager_id: Mapped[int] = mapped_column(ForeignKey("managers.id"), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    leads_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    converted_deals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversion_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    revenue: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    manager: Mapped["Manager"] = relationship(back_populates="analytics")
