"""Forgot password endpoints. They never show whether an account exists."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.auth import _password_rules
from app.services import password_recovery, rate_limit


class RecoveryRoute(APIRoute):
    # if the input is invalid, send the error without the value typed (it could be a password or token)
    def get_route_handler(self):
        handle = super().get_route_handler()

        async def handler(request: Request):
            try:
                return await handle(request)
            except RequestValidationError as error:
                detail = [{key: item[key] for key in ("loc", "msg", "type")} for item in error.errors()]
                raise HTTPException(422, detail=detail) from None

        return handler


router = APIRouter(prefix="/auth/recovery", tags=["Password recovery"], route_class=RecoveryRoute)


class RecoveryRequest(BaseModel):
    email: EmailStr


class RecoverPassword(BaseModel):
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    new_password: str = Field(max_length=128)

    _check_password = field_validator("new_password")(_password_rules)


def _config_or_error(db: Session) -> password_recovery.RecoveryConfig:
    config = password_recovery.recovery_config()
    if config is None or not password_recovery.recovery_available(db, config):
        raise HTTPException(503, "Online password recovery is unavailable. Contact ReproCare support for help.")
    return config


def _limit(*keys: str) -> None:
    # every request counts, so the email box can't be spammed
    try:
        rate_limit.check(*keys)
    except HTTPException:
        raise HTTPException(429, "Too many password recovery attempts. Please wait and try again.") from None
    rate_limit.record_failure(*keys)


@router.get("/status")
def status(db: Session = Depends(get_db)):
    return {"available": password_recovery.recovery_available(db, password_recovery.recovery_config())}


@router.post("/request", status_code=202)
def request_reset(body: RecoveryRequest, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    config = _config_or_error(db)
    email = body.email.strip().lower()
    address = request.client.host if request.client else "unknown"
    _limit(f"ip:password-recovery-request:{address}", f"password-recovery-email:{password_recovery.digest(email)}")
    # email is sent after the reply, and the reply is the same for every email
    background.add_task(password_recovery.queue_reset_email, config, email)
    return {"message": "If your account can be recovered by email, we’ll send a password reset link."}


@router.post("/reset", status_code=204)
def reset_password(body: RecoverPassword, request: Request, db: Session = Depends(get_db)):
    _config_or_error(db)
    address = request.client.host if request.client else "unknown"
    _limit(f"ip:password-recovery-reset:{address}")
    if not password_recovery.change_password_with_reset(db, body.token, body.new_password):
        raise HTTPException(400, "This password reset link is invalid or has expired. Request a new link.")