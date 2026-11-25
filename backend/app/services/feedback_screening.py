"""Relevance screening for collected public comments (ported from the integration bot).

Screening never edits or approves anything: it records reasons alongside each comment (e.g. for the bot
report). Facebook comments wait for admin moderation; on other platforms a comment that needs_holding() is
stored as held instead of being shown. Phone numbers and email addresses in displayed comments are masked
on display (see external_feedback_service.mask_contact_details).
"""

import re
from dataclasses import dataclass, field

SERVICE_TERMS = {
    "hospital", "clinic", "patient", "doctor", "doctors", "nurse", "nurses",
    "treatment", "treated", "consultation", "appointment",
    "waiting", "waited", "queue", "reception", "staff",
    "admission", "admitted", "ward", "service", "services",
    "healthcare", "outpatient", "emergency", "care", "maternity", "delivery",
    "huduma", "daktari", "muuguzi", "foleni", "kusubiri",
    "matibabu", "hospitali", "nilihudumiwa",
}

UNRELATED_PHRASES = {"passed by", "drove past", "on my way to", "political rally", "great speech"}

ABUSIVE_TERMS = {"fuck", "fucking", "bitch", "fuckers"}

PHONE = re.compile(r"(?<!\d)(?:\+?254|0)[17]\d{8}(?!\d)")
EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
# Personal health disclosures that are not shown without review (also used by the local Facebook collection view).
SENSITIVE = re.compile(
    r"\b(?:hiv|stds?|stis?|diagnos(?:ed|is)|(?:lab|test) results?|medical records?|"
    r"patient (?:id|number)|id number|identity card|my (?:pregnancy|abortion|miscarriage)|"
    r"i (?:am|was) pregnant)\b", re.I
)
SPACED_PHONE = re.compile(r"(?<!\d)(?:\+254|0)[ .-]*[17](?:[ .-]*\d){8}(?!\d)")
HOLD_REASONS = {"empty_comment", "possible_personal_information", "potentially_abusive_language", "unrelated_context"}


def needs_holding(text: str, reasons) -> bool:
    """True when a comment from a platform without a moderation queue must not be shown until reviewed."""
    return bool(HOLD_REASONS.intersection(reasons or ())) or bool(SENSITIVE.search(text) or SPACED_PHONE.search(text))

@dataclass
class ScreeningResult:
    status: str  # candidate | needs_review | irrelevant
    reasons: list[str] = field(default_factory=list)


def _contains_term(text: str, terms: set[str]) -> bool:
    return bool(set(re.findall(r"\w+", text.casefold())).intersection(terms))


def screen_feedback(hospital_name: str, comment: str, post_text: str = "", aliases=()) -> ScreeningResult:
    text = " ".join((comment or "").split()).casefold()
    context = " ".join((post_text or "").split()).casefold()

    if not text:
        return ScreeningResult("irrelevant", ["empty_comment"])
    if PHONE.search(comment) or EMAIL.search(comment):
        return ScreeningResult("needs_review", ["possible_personal_information"])
    if _contains_term(text, ABUSIVE_TERMS):
        return ScreeningResult("needs_review", ["potentially_abusive_language"])

    names = [hospital_name, *aliases]
    hospital_mentioned = any(
        len(name.strip()) >= 3 and re.search(rf"(?<!\w){re.escape(name.casefold().strip())}(?!\w)", text + " " + context)
        for name in names
        if name
    )
    service_related = _contains_term(text, SERVICE_TERMS)
    unrelated = any(phrase in text for phrase in UNRELATED_PHRASES)

    if unrelated and not service_related:
        return ScreeningResult("needs_review", ["unrelated_context"])
    if hospital_mentioned and service_related:
        return ScreeningResult("candidate", ["hospital_and_service_match"])
    if service_related:
        return ScreeningResult("candidate", ["service_related"])
    if hospital_mentioned:
        return ScreeningResult("needs_review", ["hospital_match_only"])
    return ScreeningResult("needs_review", ["general_comment"])
