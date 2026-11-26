"""Telephone number validation shared by request schemas.

Personal numbers (patients, registrations, appointment contacts) must be Kenyan mobile or landline numbers:
07…/01…/02…–06… local form, 254… or +254… international form, with optional spaces, dots, dashes or brackets.
They are stored normalised as +254XXXXXXXXX. Facility contact fields may hold several numbers and international
formats, so they are checked number by number and kept as written. Existing stored values are never rewritten.
"""

import re

_SEPARATORS = re.compile(r"[\s().\-]")
_KENYAN = re.compile(r"^(?:\+?254|0)([1-9]\d{8})$")
_INTERNATIONAL = re.compile(r"^\+[1-9]\d{7,14}$")
_SPLIT = re.compile(r"\s*(?:[;,/]|\bor\b)\s*", re.I)
PERSONAL_MESSAGE = "Enter a Kenyan phone number, for example 0712 345 678 or +254 712 345 678."
FACILITY_MESSAGE = "Enter phone numbers using digits only, for example 020 272 2541 or +254 712 345 678; separate several with commas."


def normalise_kenyan(value: str) -> str:
    """Return +254XXXXXXXXX, or raise ValueError for anything that is not a Kenyan phone number."""
    compact = _SEPARATORS.sub("", value or "")
    match = _KENYAN.match(compact)
    if not match:
        raise ValueError(PERSONAL_MESSAGE)
    return "+254" + match.group(1)


def check_facility_numbers(value: str) -> str:
    """Accept one or more Kenyan or international numbers (no letters); keep the text as written."""
    text = (value or "").strip()
    if not text:
        return ""
    for part in filter(None, _SPLIT.split(text)):
        compact = _SEPARATORS.sub("", part)
        if not (_KENYAN.match(compact) or _INTERNATIONAL.match(compact)):
            raise ValueError(FACILITY_MESSAGE)
    return text


def optional_kenyan(value: str | None) -> str | None:
    return None if value is None or not value.strip() else normalise_kenyan(value)
