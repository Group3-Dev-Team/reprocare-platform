"""Appointment requests. A request is NOT a confirmed appointment until the facility confirms it."""

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

# requested -> confirmed | declined   (by the facility)
# requested | confirmed -> cancelled  (by the patient)
# requested | confirmed -> requested  (patient proposes a new date; the facility responds again)
APPOINTMENT_STATUSES = ("requested", "confirmed", "declined", "cancelled")


class AppointmentRequest(Base):
    __tablename__ = "appointment_requests"
    __table_args__ = (
        CheckConstraint("status IN ('requested', 'confirmed', 'declined', 'cancelled')", name="ck_appointments_status"),
        CheckConstraint("preferred_time IN ('morning', 'afternoon', 'evening')", name="ck_appointments_time"),
        # One pending request per patient, facility and date. Enforced by the database so that two
        # simultaneous submissions cannot both succeed (migration 0006 adds it to existing databases).
        Index(
            "uq_appointments_pending_per_day",
            "user_id",
            "facility_id",
            "preferred_date",
            unique=True,
            postgresql_where=text("status = 'requested'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(20), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"), index=True)
    practitioner_id: Mapped[int | None] = mapped_column(ForeignKey("practitioners.id", ondelete="SET NULL"))
    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id", ondelete="SET NULL"))
    preferred_date: Mapped[date] = mapped_column(Date)
    preferred_time: Mapped[str] = mapped_column(String(20))
    contact_phone: Mapped[str] = mapped_column(String(40))
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="requested", index=True)
    facility_note: Mapped[str] = mapped_column(Text, default="")  # message from the facility when it responds
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    facility = relationship("Facility")
    practitioner = relationship("Practitioner")
    service = relationship("Service")
