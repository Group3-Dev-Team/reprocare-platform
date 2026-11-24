"""Request bodies for administrators writing health library articles.

The shapes match the seeded articles in app/database/reference_data.json ("sections" items have a heading plus
"paragraphs" and/or "list"; "references" have a label and publisher), so the public article page renders
written and seeded articles the same way.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _strip(v):
    return v.strip() if isinstance(v, str) else v


def _lines(v):
    if v is not None and any(not isinstance(line, str) or not line.strip() or len(line) > 4000 for line in v):
        raise ValueError("Paragraphs and list items must be non-empty text of at most 4000 characters.")
    return v


class ArticleSection(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    heading: str = Field(min_length=2, max_length=160)
    paragraphs: list[str] = Field(default_factory=list, max_length=30)
    items: list[str] = Field(default_factory=list, max_length=30, alias="list")  # stored as "list", like the seed data

    _strip_heading = field_validator("heading", mode="before")(_strip)
    _check_lines = field_validator("paragraphs", "items")(_lines)

    @model_validator(mode="after")
    def has_content(self):
        if not self.paragraphs and not self.items:
            raise ValueError("Each section needs at least one paragraph or list item.")
        return self

    def stored(self) -> dict:
        data = {"heading": self.heading}
        if self.paragraphs:
            data["paragraphs"] = self.paragraphs
        if self.items:
            data["list"] = self.items
        return data


class ArticleReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=3, max_length=300)
    publisher: str = Field(default="", max_length=200)

    _strip_text = field_validator("label", "publisher", mode="before")(_strip)


def _questions(v):
    if v is not None and any(not (3 <= len(q.strip()) <= 300) for q in v):
        raise ValueError("Each question must be between 3 and 300 characters.")
    return v


class ArticleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=4, max_length=200)
    category: str = Field(min_length=2, max_length=60)
    summary: str = Field(min_length=10, max_length=1000)
    read_minutes: int = Field(default=4, ge=1, le=60)
    sections: list[ArticleSection] = Field(min_length=1, max_length=30)
    questions_to_ask: list[str] = Field(default_factory=list, max_length=20)
    references: list[ArticleReference] = Field(default_factory=list, max_length=20)
    related_services: list[str] = Field(default_factory=list, max_length=20)
    review_status: str = Field(default="Awaiting clinical review", min_length=3, max_length=160)

    _strip_text = field_validator("title", "category", "summary", "review_status", mode="before")(_strip)
    _check_questions = field_validator("questions_to_ask")(_questions)

    def stored_fields(self, *, only_set: bool = False) -> dict:
        """Column values for Article, in the JSON shapes the seed data uses (related_services handled by the route)."""
        names = self.model_fields_set if only_set else set(type(self).model_fields)
        data = {}
        for name in names - {"related_services"}:
            value = getattr(self, name)
            if name == "sections":
                value = [s.stored() for s in value]
            elif name == "references":
                value = [r.model_dump() for r in value]
            elif name == "questions_to_ask":
                value = [q.strip() for q in value]
            data[name] = value
        return data


class ArticleUpdate(ArticleCreate):
    """Every field is optional; send only what changes. `null` is not accepted for any field."""

    title: str | None = Field(default=None, min_length=4, max_length=200)
    category: str | None = Field(default=None, min_length=2, max_length=60)
    summary: str | None = Field(default=None, min_length=10, max_length=1000)
    read_minutes: int | None = Field(default=None, ge=1, le=60)
    sections: list[ArticleSection] | None = Field(default=None, min_length=1, max_length=30)
    questions_to_ask: list[str] | None = Field(default=None, max_length=20)
    references: list[ArticleReference] | None = Field(default=None, max_length=20)
    related_services: list[str] | None = Field(default=None, max_length=20)
    review_status: str | None = Field(default=None, min_length=3, max_length=160)

    @model_validator(mode="after")
    def no_nulls(self):
        nulls = sorted(name for name in self.model_fields_set if getattr(self, name) is None)
        if nulls:
            raise ValueError(f"These fields cannot be empty: {', '.join(nulls)}.")
        return self
