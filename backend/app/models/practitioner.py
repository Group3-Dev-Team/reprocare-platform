"""Healthcare practitioners listed in the specialist directory."""

from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Practitioner(Base):
    __tablename__ = "practitioners"
    __table_args__ = (
        CheckConstraint(
            "registration_status IN ('matched', 'not_checked', 'unresolved')",
            name="ck_practitioners_registration_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160), index=True)
    title: Mapped[str] = mapped_column(String(120))  # e.g. "Obstetrician & gynaecologist"
    specialty: Mapped[str] = mapped_column(String(120), index=True)
    town: Mapped[str] = mapped_column(String(80), index=True)
    gender: Mapped[str] = mapped_column(String(20), default="")
    languages: Mapped[str] = mapped_column(String(255), default="")  # comma-separated
    offers_telehealth: Mapped[bool] = mapped_column(Boolean, default=False)
    bio: Mapped[str] = mapped_column(Text, default="")
    fee_note: Mapped[str] = mapped_column(String(160), default="")
    facility_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id", ondelete="SET NULL"), index=True)

    registration_status: Mapped[str] = mapped_column(String(20), default="not_checked")
    registration_body: Mapped[str] = mapped_column(String(120), default="")
    registration_code: Mapped[str] = mapped_column(String(60), default="")
    registration_checked_on: Mapped[date | None] = mapped_column(Date)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    facility = relationship("Facility")
