"""Automatic publication screening for collected public comments.

Every comment gets exactly one decision, with a reason:

* ``publish``: relevant to the facility's care, services, costs, insurance, access or staff, with no personal
  health disclosure. Phone numbers and email addresses are masked before storage.
* ``review``: personal health details, serious allegations or abusive language, or a longer comment whose
  relevance is uncertain. Kept held for an administrator.
* ``exclude``: not feedback: greetings, prayers, tags of friends, job requests, advertising, contact details
  only, hashtags, repeated text or content from a page that is not the facility's own.

Rules are deterministic so every decision can be explained and re-run. They extend
``feedback_screening.screen_feedback`` and use its personal-health pattern unchanged.
"""

import re
from dataclasses import dataclass

from app.services.feedback_screening import EMAIL, SENSITIVE, SPACED_PHONE, screen_feedback

WORD = re.compile(r"[\w']+", re.UNICODE)

RELEVANT = {
    # care and services
    "hospital", "clinic", "doctor", "doctors", "dr", "nurse", "nurses", "staff", "patient", "patients", "care",
    "service", "services", "treatment", "treated", "consultation", "appointment", "admitted", "admission", "ward",
    "maternity", "delivery", "deliver", "delivered", "birth", "antenatal", "anc", "postnatal", "cs", "caesarean",
    "c-section", "fertility", "ivf", "gynaecologist", "gynecologist", "gynae", "obstetrician", "family", "planning",
    "contraception", "contraceptive", "implant", "coil", "iud", "pap", "smear", "screening", "cancer", "fistula",
    "ultrasound", "scan", "xray", "x-ray", "mri", "ct", "lab", "laboratory", "test", "tests", "testing", "results",
    "specialist", "surgery", "theatre", "operation", "pharmacy", "drugs", "medicine", "medication", "vaccine",
    "vaccination", "immunization", "clinic's", "outpatient", "inpatient", "emergency", "ambulance", "reception",
    "receptionist's", "queue", "waiting", "waited", "mama", "baby", "babies", "newborn", "child", "children",
    # cost, insurance, access
    "price", "prices", "cost", "costs", "charge", "charges", "fee", "fees", "pay", "payment", "cash", "free",
    "affordable", "expensive", "cheap", "discount", "nhif", "sha", "shif", "insurance", "insurer", "cover",
    "covered", "jubilee", "aar", "madison", "britam", "cic", "card", "branch", "branches", "location", "located",
    "open", "hours", "weekend", "sunday", "saturday", "book", "booking", "available", "offer", "offers",
    # experience
    "best", "good", "great", "excellent", "amazing", "wonderful", "professional", "friendly", "kind", "caring",
    "helpful", "clean", "recommend", "recommended", "poor", "bad", "worst", "rude", "slow", "dirty", "negligent",
    "negligence", "served", "serving", "attended", "experience", "quality", "dedicated", "efficient",
    # Swahili and Sheng
    "huduma", "daktari", "muuguzi", "hospitali", "matibabu", "dawa", "bei", "pesa", "peso", "ngapi", "bure",
    "kujifungua", "mzuri", "nzuri", "safi", "mbaya", "wagonjwa", "mgonjwa", "foleni", "kliniki",
    "treat", "treats", "fibroid", "fibroids", "surrogate", "surrogacy", "sperm", "eggs", "pregnancy", "pregnant",
    "client", "clients", "helping", "kudos", "doctor's", "consultant", "midwife", "midwives", "package", "packages",
    "procedure", "procedures", "colonoscopy", "endoscopy", "ogd", "mammogram", "biopsy", "dialysis", "physiotherapy",
    "dental", "dentist", "optical", "eye", "ent", "icu", "hdu", "mnafanya", "mnafanyanga", "mnatoa", "mnakubali",
}
MEDICAL_SUFFIX = re.compile(r"\w+(?:scopy|ectomy|otomy|plasty|ology|ologist|itis|gram|graphy|therapy)\b", re.I)
QUESTION_CUES = ("how much", "how many", "do you", "do u", "does ", "is there", "are you", "can i", "can we",
                 "where is", "where are", "which branch", "when do", "what is the", "what are", "ni ngapi",
                 "ni pesa", "ama ni bure", "bei gani", "mko wapi", "mko na wapi")
# A question addressed to the facility about what it offers, even without a care word ("How much?", "Do you treat X?")
DIRECT_QUESTION = re.compile(r"^(?:how much|how many|do (?:you|u)|does (?:the|this|it|your)|is there|are (?:you|there)|"
                             r"can (?:i|we|one)|where (?:is|are)|which branch|when (?:do|does|is|are)|ni ngapi|bei gani|"
                             r"mko (?:na )?wapi)\b", re.I)
GREETING_OR_PRAYER = re.compile(
    r"^(?:(?:happy|merry)\s+\w+(?:\s+\w+)?|congrat\w*|eid\s+mubarak|amen+|hallelujah|praise\s+(?:god|the\s+lord)|"
    r"thanks?\s+be\s+to\s+god|god\s+bless\w*|blessings?|may\s+(?:the\s+)?(?:almighty|god|lord)\b|"
    r"good\s+(?:morning|evening|night)|hello|hi|hey|wow|nice|ok(?:ay)?|same|yes|no|true|indeed)\b", re.I)
JOB_SEEKING = re.compile(r"\b(?:vacanc\w*|jobs|any (?:job|opening|chance)|employ(?:ment|ing)?|hiring|recruit\w*|"
                         r"intern(?:ship)?s?|attachment|cv|curriculum vitae|how (?:can|do) i apply|send (?:my )?application|"
                         r"looking for (?:a )?(?:job|work)|nipe kazi|kazi yoyote|tunaomba kazi|need (?:a )?job|(?:apply|applied) (?:for|to work)|"
                         r"land an opportunity|opportunity to work|work (?:here|with you)|train with you|vacant|hire\w*)\b", re.I)
JOB_TITLE_ONLY = re.compile(r"^(?:a\s+)?(?:receptionist|driver|nurse|cleaner|cook|guard|accountant|clinical officer|"
                            r"lab tech\w*|pharmacist|cashier|security)\W*$", re.I)
PROMOTION = re.compile(r"(?:https?://|www\.|\$\s?\d|\busd\b|bitcoin|crypto|forex|whatsapp me|inbox me|dm me|"
                       r"click (?:here|the link)|follow (?:me|my page)|earn \d|small business(?:es)?|domain|website builder)",
                       re.I)
SERIOUS_ALLEGATION = re.compile(r"\b(?:died|death|killed|murder\w*|stole|stolen|theft|fraud\w*|conned|sued?|lawsuit|"
                                r"detained|detain(?:ing|s)?|negligen\w*|malpractice|raped?|abused)\b", re.I)
ABUSIVE = re.compile(r"\b(?:fuck\w*|bitch\w*|idiot\w*|stupid|mavi|malaya|kumbaff?u)\b", re.I)
HASHTAG_OR_MENTION = re.compile(r"[#@][\w.]+")
PHONE_ANY = re.compile(r"(?<!\d)(?<!\d[,.])(?:(?:\+?254|0)[ .-]*)?[17]\d{2}[ .-]*\d{3}[ .-]*\d{3}(?!\d|[,.]\d)")

# First-person statements about the writer's (or their family's) own health condition: held for review, never published
# automatically, even when the comment is otherwise about the facility ("I am a cancer victim", "my wife had a miscarriage").
PERSONAL_CONDITION = re.compile(
    r"\b(?:i\s*a?m|i'm|iam|im|i\s+(?:was|have|had|got|suffer\w*|lost)|my|me|mine|our)\b[^.?!]{0,40}?\b(?:cancer|hiv|aids|tb|"
    r"tuberculosis|diabet\w*|infertil\w*|barren|miscarr\w*|abort\w*|pregnan\w*|stis?|stds?|fibroids?|cysts?|hepatitis|"
    r"epilep\w*|depress\w*|tumou?rs?|victim|survivor|stillbirth|still born|stillborn|sickle cell|kidney failure|stroke|"
    r"chemo\w*|dialysis|positive)\b", re.I)

PUBLISH, REVIEW, EXCLUDE = "publish", "review", "exclude"


@dataclass(frozen=True)
class Decision:
    action: str  # publish | review | exclude
    reason: str


def normalise(text: str) -> str:
    return " ".join((text or "").split())


def duplicate_key(author: str, text: str) -> str:
    return normalise(author).casefold() + "|" + re.sub(r"\W+", " ", normalise(text).casefold()).strip()


def mask_contacts(text: str) -> str:
    """Mask phone numbers and email addresses before a comment is stored for publication."""
    text = PHONE_ANY.sub("[phone number removed]", text)
    return EMAIL.sub("[email removed]", text)


GENERIC_NAME_WORDS = {"the", "hospital", "hospitals", "clinic", "medical", "centre", "center", "kenya", "ltd", "limited",
                      "healthcare", "health", "care", "group", "of", "and", "mission", "maternity", "nursing", "home",
                      "official", "services", "laboratory", "laboratories", "diagnostics", "specialist", "women", "womens"}


def _tokens(value: str) -> list[str]:
    import unicodedata

    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().casefold()
    return re.findall(r"[a-z0-9]+", value)


def is_facility_author(author: str, facility_name: str, page_id: str = "") -> bool:
    """True when the commenter is the facility's own page ("Marie Stopes Kenya" on marie.stopes.kenya.1985).

    Every distinctive word of the author's name must appear in the facility name or page id, so a person who shares
    one word with the facility ("Karen Wanjiru" on The Karen Hospital) is not mistaken for it.
    """
    words = [w for w in _tokens(author) if w not in GENERIC_NAME_WORDS and len(w) >= 3]
    if not words:
        return False
    haystack = " ".join(_tokens(facility_name)) + " " + "".join(_tokens(page_id))
    return all(w in haystack for w in words)


def classify(text: str, facility_name: str = "", post_text: str = "", by_facility: bool = False,
             is_reply: bool = False) -> Decision:
    clean = normalise(text)
    if not clean:
        return Decision(EXCLUDE, "empty")
    words = WORD.findall(clean.casefold())
    without_contacts = normalise(EMAIL.sub(" ", SPACED_PHONE.sub(" ", PHONE_ANY.sub(" ", clean))))
    if not WORD.findall(without_contacts):
        return Decision(EXCLUDE, "contact_details_only")
    if not WORD.findall(HASHTAG_OR_MENTION.sub(" ", clean)):
        return Decision(EXCLUDE, "hashtags_or_mentions_only")
    if SENSITIVE.search(clean) or PERSONAL_CONDITION.search(clean):
        return Decision(REVIEW, "personal_health_detail")
    if ABUSIVE.search(clean):
        return Decision(REVIEW, "abusive_language")
    if SERIOUS_ALLEGATION.search(clean):
        return Decision(REVIEW, "serious_allegation")
    if by_facility:
        # the facility answering someone is useful context; its own top-level comments are announcements
        return Decision(PUBLISH, "facility_reply") if is_reply else Decision(EXCLUDE, "facility_own_comment")
    if PROMOTION.search(clean):
        return Decision(EXCLUDE, "advertising_or_off_topic_promotion")
    if JOB_SEEKING.search(clean) or JOB_TITLE_ONLY.match(clean):
        return Decision(EXCLUDE, "job_request")

    relevant = bool(set(words) & RELEVANT) or bool(MEDICAL_SUFFIX.search(clean)) or screen_feedback(facility_name, clean, post_text).status == "candidate"
    question = "?" in clean or any(cue in clean.casefold() for cue in QUESTION_CUES)
    greeting = bool(GREETING_OR_PRAYER.match(clean))

    if relevant or DIRECT_QUESTION.match(clean):
        return Decision(PUBLISH, "service_question" if question else "care_experience_or_service_comment")
    if greeting:
        return Decision(EXCLUDE, "greeting_or_prayer_only")
    if len(words) <= 3:
        # one to three words with no care-related term: a tag of a friend ("N Njoki"), "Interested", "Same"
        return Decision(EXCLUDE, "too_short_or_tag_only")
    if len(words) >= 8:
        return Decision(REVIEW, "uncertain_relevance")
    return Decision(EXCLUDE, "not_about_care")
