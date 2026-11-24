"""Sign up, sign in, sign out and the signed-in user's own account."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import User
from app.schemas.auth import AccountClosure, LoginRequest, PasswordChange, ProfileUpdate, RegisterRequest
from app.schemas.google_auth import GoogleExchange, GoogleLinkStart, GoogleStart
from app.services import google_oidc, rate_limit
from app.services.account_closure import close_account
from app.services.auth_service import (
    create_session,
    demo_accounts_blocked,
    end_other_sessions,
    end_session,
    get_current_user,
    get_session_token,
    hash_password,
    user_to_dict,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _limit_registration(request: Request) -> None:
    """Every sign-up attempt counts, as contact messages do: 40 from one address in 15 minutes
    (the shared-address limit, because offices and campuses share one IP)."""
    key = f"ip:register:{request.client.host if request.client else 'unknown'}"
    try:
        rate_limit.check(key)
    except HTTPException:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Too many sign-up attempts from this network. Please wait 15 minutes and try again."
        ) from None
    rate_limit.record_failure(key)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    _limit_registration(request)
    email = body.email.strip().lower()
    if email.endswith("@reprocare.demo"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This email domain is reserved for demonstration accounts.")
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists. Sign in instead.")
    # sign up always makes a patient, staff and admin accounts are created by an admin
    user = User(email=email, full_name=body.full_name.strip(), phone=body.phone, password_hash=hash_password(body.password), role="patient")
    try:
        db.add(user)
        db.flush()
        token = create_session(db, user)
        result = {"token": token, "user": user_to_dict(user)}
        db.commit()
    except IntegrityError as error:
        db.rollback()
        # two sign ups with the same email at the same moment
        if getattr(error.orig, "sqlstate", None) == "23505" and error.orig.diag.constraint_name == "ix_users_email":
            raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists. Sign in instead.") from None
        raise
    return result


@router.post("/login")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    keys = (f"email:{email}", f"ip:{client_ip}")
    rate_limit.check(*keys)
    user = db.scalar(select(User).where(func.lower(User.email) == email).with_for_update())
    # always run the password check so a wrong email takes as long as a wrong password
    if not verify_password(body.password, user.password_hash if user else None) or user is None:
        rate_limit.record_failure(*keys)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "The email or password is incorrect.")
    rate_limit.reset(f"email:{email}")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated. Contact ReproCare support.")
    if demo_accounts_blocked(email):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Demonstration accounts are disabled on this server.")
    token = create_session(db, user)
    result = {"token": token, "user": user_to_dict(user)}
    db.commit()
    return result


@router.get("/capabilities")
def capabilities(db: Session = Depends(get_db)):
    # frontend uses this to know if it should show the Google button
    return {"google": google_oidc.enabled(db)}


@router.post("/google/start")
def google_start(body: GoogleStart, request: Request, db: Session = Depends(get_db)):
    address = request.client.host if request.client else "unknown"
    return google_oidc.begin(db, body, address)


@router.post("/google/exchange")
def google_exchange(body: GoogleExchange, request: Request, db: Session = Depends(get_db)):
    address = request.client.host if request.client else "unknown"
    return google_oidc.finish(db, body, address)


@router.get("/google/link")
def google_link_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return google_oidc.link_status(db, user)


@router.post("/google/link/start")
def google_link_start(
    body: GoogleLinkStart, request: Request,
    user: User = Depends(get_current_user), token: str = Depends(get_session_token),
    db: Session = Depends(get_db),
):
    address = request.client.host if request.client else "unknown"
    return google_oidc.begin_link(db, body, user, token, address)


@router.post("/google/link/exchange", status_code=status.HTTP_204_NO_CONTENT)
def google_link_exchange(
    body: GoogleExchange, request: Request,
    user: User = Depends(get_current_user), token: str = Depends(get_session_token),
    db: Session = Depends(get_db),
):
    address = request.client.host if request.client else "unknown"
    google_oidc.finish_link(db, body, user, token, address)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(token: str = Depends(get_session_token), db: Session = Depends(get_db)):
    end_session(db, token)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_to_dict(user)


@router.patch("/me")
def update_me(body: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.full_name = body.full_name.strip()
    user.phone = body.phone
    db.commit()
    return user_to_dict(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: PasswordChange,
    user: User = Depends(get_current_user),
    token: str = Depends(get_session_token),
    db: Session = Depends(get_db),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password is incorrect.")
    if body.current_password == body.new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose a new password that is different from the current one.")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    # sign out every other device, this one stays signed in
    end_other_sessions(db, user, keep_token=token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Sign out on every device, including this one."""
    end_other_sessions(db, user)


@router.post("/me/close", status_code=status.HTTP_204_NO_CONTENT)
def close_my_account(body: AccountClosure, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Close your own patient account. Staff and admin accounts are closed by an admin."""
    if user.role != "patient":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Staff and administrator accounts are closed by a ReproCare administrator. Please contact us.")
    if body.confirm_email.strip().lower() != user.email.lower():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Type the email address for this account to confirm.")
    # accounts made with Google have no password, so they only confirm the email
    google_only = not body.password and google_oidc.has_identity(db, user)
    if not google_only and not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your password is incorrect.")
    close_account(db, user)