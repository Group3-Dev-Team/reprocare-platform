"""Health library articles and Contact Us messages."""

from datetime import date, datetime

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(60), index=True)
    summary: Mapped[str] = mapped_column(Text)
    read_minutes: Mapped[int] = mapped_column(Integer, default=4)
    # [{"heading": str, "paragraphs": [str], "list": [str]}]
    sections: Mapped[list] = mapped_column(JSON, default=list)
    questions_to_ask: Mapped[list] = mapped_column(JSON, default=list)
    references: Mapped[list] = mapped_column(JSON, default=list)  # [{"label": str, "publisher": str}]
    related_services: Mapped[str] = mapped_column(String(255), default="")  # comma-separated service slugs
    review_status: Mapped[str] = mapped_column(String(160), default="Awaiting clinical review")
    updated_on: Mapped[date | None] = mapped_column(Date)


class ContactMessage(Base):
    __tablename__ = "contact_messages"
    __table_args__ = (
        CheckConstraint("status IN ('new', 'in_progress', 'resolved')", name="ck_contact_status"),
        CheckConstraint(
            "topic IN ('general', 'listing_correction', 'privacy', 'technical', 'feedback')", name="ck_contact_topic"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(20), unique=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255))
    topic: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
