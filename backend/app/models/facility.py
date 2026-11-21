"""Healthcare facilities and the reference data attached to them: services, insurers and laboratory tests."""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

FACILITY_TYPES = ("hospital", "clinic", "maternity_home", "health_centre", "laboratory")

facility_services = Table(
    "facility_services",
    Base.metadata,
    Column("facility_id", ForeignKey("facilities.id", ondelete="CASCADE"), primary_key=True),
    Column("service_id", ForeignKey("services.id", ondelete="CASCADE"), primary_key=True),
)

facility_insurers = Table(
    "facility_insurers",
    Base.metadata,
    Column("facility_id", ForeignKey("facilities.id", ondelete="CASCADE"), primary_key=True),
    Column("insurer_id", ForeignKey("insurers.id", ondelete="CASCADE"), primary_key=True),
)


class Service(Base):
    """A reproductive-health service people search for, e.g. 'Antenatal care'."""

    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    short_description: Mapped[str] = mapped_column(String(160), default="")
    # Comma-separated search words, including Kiswahili terms (e.g. "pregnancy,mimba").
    keywords: Mapped[str] = mapped_column(Text, default="")


class Insurer(Base):
    """An insurer or public scheme. Acceptance is what facilities report; ReproCare does not decide cover."""

    __tablename__ = "insurers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(80), default="Private insurer")
    note: Mapped[str] = mapped_column(Text, default="")


class Facility(Base):
    __tablename__ = "facilities"
    __table_args__ = (
        CheckConstraint(
            "facility_type IN ('hospital', 'clinic', 'maternity_home', 'health_centre', 'laboratory')",
            name="ck_facilities_type",
        ),
        CheckConstraint(
            "registration_status IN ('matched', 'not_checked', 'unresolved')",
            name="ck_facilities_registration_status",
        ),
        # One record per external identifier per source, so imports can update instead of duplicating.
        UniqueConstraint("source_id", "external_id", name="uq_facilities_source_external"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    facility_type: Mapped[str] = mapped_column(String(30), index=True)
    description: Mapped[str] = mapped_column(Text, default="")

    # Location
    address: Mapped[str] = mapped_column(String(255), default="")
    area: Mapped[str] = mapped_column(String(120), default="")
    town: Mapped[str] = mapped_column(String(80), index=True)
    county: Mapped[str] = mapped_column(String(80), index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    # Contact
    phone: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    website: Mapped[str] = mapped_column(String(255), default="")

    # Opening hours and access
    weekday_hours: Mapped[str] = mapped_column(String(60), default="")
    saturday_hours: Mapped[str] = mapped_column(String(60), default="")
    sunday_hours: Mapped[str] = mapped_column(String(60), default="")
    open_24_hours: Mapped[bool] = mapped_column(Boolean, default=False)
    open_weekends: Mapped[bool] = mapped_column(Boolean, default=False)
    languages: Mapped[str] = mapped_column(String(255), default="")  # comma-separated
    payment_methods: Mapped[str] = mapped_column(String(255), default="")  # comma-separated
    accessibility: Mapped[str] = mapped_column(Text, default="")  # comma-separated
    offers_telehealth: Mapped[bool] = mapped_column(Boolean, default=False)
    accepts_appointment_requests: Mapped[bool] = mapped_column(Boolean, default=False)

    # Official registration layer (see docs/FEATURES.md, "three information layers")
    registration_status: Mapped[str] = mapped_column(String(20), default="not_checked")
    registration_body: Mapped[str] = mapped_column(String(160), default="")
    registration_code: Mapped[str] = mapped_column(String(60), default="")
    registration_checked_on: Mapped[date | None] = mapped_column(Date)

    # Provenance
    image_key: Mapped[str] = mapped_column(String(40), default="")  # a bundled frontend image, e.g. "facility"
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id", ondelete="SET NULL"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(160))  # e.g. a Google place ID or KMHFL code
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    services = relationship("Service", secondary=facility_services, order_by="Service.name")
    insurers = relationship("Insurer", secondary=facility_insurers, order_by="Insurer.name")
    lab_tests = relationship("LabTest", back_populates="facility", cascade="all, delete-orphan", order_by="LabTest.name")
    source = relationship("DataSource")


class LabTest(Base):
    __tablename__ = "lab_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    sample_type: Mapped[str] = mapped_column(String(120), default="")
    turnaround: Mapped[str] = mapped_column(String(60), default="")
    price_note: Mapped[str] = mapped_column(String(80), default="")  # provider-stated, free text
    home_collection: Mapped[bool] = mapped_column(Boolean, default=False)

    facility = relationship("Facility", back_populates="lab_tests")
