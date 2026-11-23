"""Google sign-in tables: linked Google accounts and one-use sign-in attempts."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class GoogleIdentity(Base):
    __tablename__ = "google_identities"

    # "subject" is Google's id for the person, one Google account per user
    subject: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)


class GoogleAuthorization(Base):
    __tablename__ = "google_authorizations"

    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    challenge: Mapped[str] = mapped_column(String(43))
    nonce: Mapped[str] = mapped_column(String(64))
    intent: Mapped[str] = mapped_column(String(12))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class GoogleLinkAuthorization(Base):
    # used when a signed in user links Google to their account
    __tablename__ = "google_link_authorizations"

    state_hash: Mapped[str] = mapped_column(
        ForeignKey("google_authorizations.state_hash", ondelete="CASCADE"), primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    binding: Mapped[str] = mapped_column(String(64))