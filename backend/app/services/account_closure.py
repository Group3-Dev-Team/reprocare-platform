"""Close my account (patients only).

Signs the person out everywhere and removes or hides their personal data:
* the user row stays (other tables point to it) but email, name, phone and password are replaced
  and the account is turned off, so the same email can sign up again
* sessions, notifications, saved clinics, reset links and Google links are deleted
* open appointment requests are cancelled (clinic gets told) and lose the phone number and notes
* pending reviews are deleted, published ones stay under a neutral name
* programme registrations are cancelled and lose the name and phone

Contact messages are kept because they may contain a privacy request the admin must answer.
"""

import secrets

from sqlalchemy import column, delete, inspect, select, table, update
from sqlalchemy.orm import Session

from app.models import AppointmentRequest, Notification, ProgramRegistration, Review, SavedFacility, User, UserSession
from app.services.auth_service import hash_password
from app.services.common import notify

CLOSED_NAME = "Closed account"
FORMER_AUTHOR = "Former ReproCare user"


def _has_table(db: Session, name: str) -> bool:
    return inspect(db.get_bind()).has_table(name)


def close_account(db: Session, user: User) -> None:
    # tell the clinic staff about any open requests before cancelling them
    open_requests = db.scalars(
        select(AppointmentRequest).where(AppointmentRequest.user_id == user.id, AppointmentRequest.status.in_(("requested", "confirmed")))
    ).all()
    for appointment in open_requests:
        for staff in db.scalars(select(User).where(User.facility_id == appointment.facility_id, User.is_active.is_(True))):
            notify(db, staff.id, "Request cancelled: account closed", appointment.reference, "/dashboard/facility/appointments")
    db.execute(
        update(AppointmentRequest)
        .where(AppointmentRequest.user_id == user.id, AppointmentRequest.status.in_(("requested", "confirmed")))
        .values(status="cancelled")
    )
    db.execute(update(AppointmentRequest).where(AppointmentRequest.user_id == user.id).values(contact_phone="", notes=""))

    db.execute(delete(Review).where(Review.user_id == user.id, Review.status == "pending"))
    db.execute(update(Review).where(Review.user_id == user.id).values(author_name=FORMER_AUTHOR, user_id=None))

    db.execute(
        update(ProgramRegistration)
        .where(ProgramRegistration.user_id == user.id, ProgramRegistration.status == "registered")
        .values(status="cancelled")
    )
    db.execute(update(ProgramRegistration).where(ProgramRegistration.user_id == user.id).values(full_name=CLOSED_NAME, phone=""))

    db.execute(delete(SavedFacility).where(SavedFacility.user_id == user.id))
    db.execute(delete(Notification).where(Notification.user_id == user.id))
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    # these tables only exist after migrations 0004 and 0005
    for name in ("password_resets", "google_identities", "google_link_authorizations"):
        if _has_table(db, name):
            linked = table(name, column("user_id"))
            db.execute(delete(linked).where(linked.c.user_id == user.id))

    user.email = f"closed-{user.id}-{secrets.token_hex(6)}@closed.invalid"
    user.full_name = CLOSED_NAME
    user.phone = None
    user.password_hash = hash_password(secrets.token_urlsafe(32))
    user.facility_id = None
    user.is_active = False
    db.commit()