"""Provision one administrator on the configured local development database."""

import argparse
import getpass
import os
import sys
import warnings

from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import SessionLocal, engine
from app.models import User
from app.services.auth_service import DEMO_EMAIL_DOMAIN, hash_password


def _password_rules(value: str) -> str:
    # Mirrors the registration password rules in app/schemas/auth.py (SCRUM-8), kept local so this tool
    # does not depend on the authentication workstream's schemas.
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password is too long. Use 72 characters or fewer.")
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if not any(c.isdigit() for c in value) or not any(c.isalpha() for c in value):
        raise ValueError("Password must contain letters and at least one number.")
    return value


class AdminAccount(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(max_length=128)

    _check_password = field_validator("password")(_password_rules)


class ProvisioningError(Exception):
    """A provisioning failure safe to display without credentials."""


def _require_local_development() -> None:
    url = engine.url
    loopback = {"localhost", "127.0.0.1", "::1"}
    # Connection options must not redirect the explicit loopback address.
    if (
        settings.environment != "development"
        or url.get_backend_name() != "postgresql"
        or url.host not in loopback
        or not url.database
        or url.query.keys() & {"host", "hostaddr", "service"}
        or os.getenv("PGSERVICE")
        or ((hostaddr := os.getenv("PGHOSTADDR")) and hostaddr not in loopback)
    ):
        raise ProvisioningError("Administrator provisioning requires a loopback PostgreSQL database in development mode.")


def provision_admin(db: Session, *, email: str, full_name: str, password: str) -> bool:
    """Create an active administrator. Return False when that administrator already exists."""
    try:
        account = AdminAccount(email=email.strip(), full_name=full_name.strip(), password=password)
    except ValidationError as error:
        field = error.errors(include_input=False, include_context=False, include_url=False)[0]["loc"][0]
        message = {
            "email": "Enter a valid administrator email address.",
            "full_name": "Enter a name between 2 and 120 characters.",
            "password": "Use 10 or more characters with letters and numbers, up to 72 UTF-8 bytes.",
        }[field]
        raise ProvisioningError(message) from None
    if len(password) < 10:
        raise ProvisioningError("Use 10 or more characters with letters and numbers, up to 72 UTF-8 bytes.")

    normalized_email = account.email.lower()
    if normalized_email.endswith(DEMO_EMAIL_DOMAIN):
        raise ProvisioningError("Choose an email outside the reserved demonstration domain.")

    lookup = select(User).where(func.lower(User.email) == normalized_email)
    existing = db.scalar(lookup)
    if existing is None:
        statement = insert(User).values(
            email=normalized_email,
            full_name=account.full_name,
            password_hash=hash_password(account.password),
            role="admin",
            is_active=True,
        ).on_conflict_do_nothing(index_elements=[User.email]).returning(User.id)
        if db.scalar(statement) is not None:
            db.commit()
            return True
        # Another request may have created the account after our first lookup.
        existing = db.scalar(lookup)

    if existing is not None and existing.role == "admin" and existing.is_active:
        return False
    raise ProvisioningError("That email could not be provisioned. Existing accounts are left unchanged.")


def main(argv: list[str] | None = None) -> None:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    try:
        _require_local_development()
        if not sys.stdin.isatty():
            raise ProvisioningError("Run this command from an interactive terminal.")
        email = input("Administrator email: ")
        full_name = input("Administrator name: ")
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("New administrator password: ")
            confirmation = getpass.getpass("Confirm administrator password: ")
        if password != confirmation:
            raise ProvisioningError("The passwords did not match.")
        with SessionLocal() as db:
            created = provision_admin(db, email=email, full_name=full_name, password=password)
    except (EOFError, KeyboardInterrupt):
        raise SystemExit("Administrator setup cancelled.") from None
    except getpass.GetPassWarning:
        raise SystemExit("This terminal could not securely read the password.") from None
    except ProvisioningError as error:
        raise SystemExit(str(error)) from None
    except SQLAlchemyError:
        raise SystemExit("Administrator setup could not reach the initialized development database.") from None

    print("Administrator created." if created else "An active administrator already uses that email.")


if __name__ == "__main__":
    main()
