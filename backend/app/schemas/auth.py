"""Request bodies for registration, sign-in and profile changes."""

from app.services.phone import optional_kenyan
from pydantic import BaseModel, EmailStr, Field, field_validator


def _password_rules(value: str) -> str:
    # bcrypt only reads 72 bytes, longer passwords gave a 500 error
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password is too long. Use 72 characters or fewer.")
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if not any(c.isdigit() for c in value) or not any(c.isalpha() for c in value):
        raise ValueError("Password must contain letters and at least one number.")
    return value


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(max_length=128)
    phone: str | None = Field(default=None, max_length=40)

    _check_password = field_validator("password")(_password_rules)
    _check_phone = field_validator("phone")(optional_kenyan)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=40)

    _check_phone = field_validator("phone")(optional_kenyan)


class AccountClosure(BaseModel):
    # user types their email (and password if they have one) to confirm closing the account
    confirm_email: str = Field(min_length=3, max_length=255)
    password: str = Field(default="", max_length=128)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(max_length=128)

    _check_password = field_validator("new_password")(_password_rules)