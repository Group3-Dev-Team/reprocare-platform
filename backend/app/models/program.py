"""Community health programmes (outreach events) and the registrations people make for them."""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class CommunityProgram(Base):
    __tablename__ = "community_programs"
    __table_args__ = (
        CheckConstraint("program_type IN ('screening', 'testing', 'education', 'outreach')", name="ck_programs_type"),
        CheckConstraint("cost_type IN ('free', 'subsidised', 'paid')", name="ck_programs_cost"),
        CheckConstraint("status IN ('published', 'draft', 'cancelled')", name="ck_programs_status"),
        CheckConstraint("capacity > 0", name="ck_programs_capacity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    program_type: Mapped[str] = mapped_column(String(20), index=True)
    summary: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    organizer_name: Mapped[str] = mapped_column(String(160))
    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id", ondelete="SET NULL"), index=True)
    host_facility_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id", ondelete="SET NULL"))
    venue: Mapped[str] = mapped_column(String(255))
    town: Mapped[str] = mapped_column(String(80), index=True)
    county: Mapped[str] = mapped_column(String(80))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    start_date: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[str] = mapped_column(String(20))
    end_time: Mapped[str] = mapped_column(String(20))
    eligibility: Mapped[str] = mapped_column(Text, default="")
    requirements: Mapped[str] = mapped_column(Text, default="")
    cost_type: Mapped[str] = mapped_column(String(20), default="free", index=True)
    cost_note: Mapped[str] = mapped_column(String(255), default="")
    capacity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="published")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    service = relationship("Service")
    host_facility = relationship("Facility")


class ProgramRegistration(Base):
    __tablename__ = "program_registrations"
    __table_args__ = (
        UniqueConstraint("program_id", "user_id", name="uq_registrations_program_user"),
        CheckConstraint("status IN ('registered', 'cancelled', 'attended')", name="ck_registrations_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(20), unique=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("community_programs.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="registered")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    program = relationship("CommunityProgram")
