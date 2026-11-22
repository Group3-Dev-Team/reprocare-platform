"""Requests for Google sign-in. The Google keys stay on the server."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class GoogleStart(BaseModel):
    # random code from the browser, checked again when Google sends the user back
    challenge: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    intent: Literal["sign-in", "register"]
    accept_terms: bool = False

    @model_validator(mode="after")
    def require_registration_consent(self):
        if self.intent == "register" and not self.accept_terms:
            raise ValueError("Accept the terms and privacy notice to create your account.")
        return self


class GoogleLinkStart(BaseModel):
    # linking Google to an existing account needs the current password first
    challenge: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    current_password: str = Field(min_length=1, max_length=128)


class GoogleExchange(BaseModel):
    code: str = Field(min_length=1, max_length=2048)
    state: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    verifier: str = Field(pattern=r"^[A-Za-z0-9._~-]{43,128}$")