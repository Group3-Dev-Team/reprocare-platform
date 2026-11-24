"""Import structured facility records from an external source (the independent data bot, a registry export...).

Rules:
* Each record is validated on its own; one bad record does not stop the batch.
* (source, external_id) is the stable identifier. A known pair updates the existing record; a new pair creates one.
* A record that matches another facility's name and town is still created, but reported as a possible duplicate.
* Every batch is written to `import_batches`, so imports can be audited.
"""

import re

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DataSource, Facility, ImportBatch, Insurer, Service
from app.schemas.data_import import ImportFacility, ImportRequest


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:100]


def unique_slug(db: Session, base: str) -> str:
    slug, n = base, 2
    while db.scalar(select(Facility.id).where(Facility.slug == slug)):
        slug, n = f"{base}-{n}", n + 1
    return slug


def get_or_create_source(db: Session, code: str, name: str | None, attribution: str | None) -> DataSource:
    source = db.scalar(select(DataSource).where(DataSource.code == code))
    if source is None:
        source = DataSource(code=code, name=name or code.replace("_", " ").title(), attribution=attribution or "")
        db.add(source)
        db.flush()
    return source


def _apply(facility: Facility, record: ImportFacility, services: list[Service], insurers: list[Insurer]) -> None:
    for field in (
        "name", "facility_type", "town", "county", "address", "area", "latitude", "longitude", "phone", "email",
        "website", "description", "weekday_hours", "saturday_hours", "sunday_hours", "open_24_hours",
    ):
        setattr(facility, field, getattr(record, field))
    facility.open_weekends = bool(record.saturday_hours or record.sunday_hours or record.open_24_hours)
    facility.registration_status = record.registration.status
    facility.registration_body = record.registration.body
    facility.registration_code = record.registration.code
    facility.registration_checked_on = record.registration.checked_on
    facility.services = services
    facility.insurers = insurers


def import_facilities(db: Session, payload: ImportRequest, submitted_by_user_id: int | None = None) -> dict:
    source = get_or_create_source(db, payload.source.code, payload.source.name, payload.source.attribution)
    services_by_slug = {s.slug: s for s in db.scalars(select(Service))}
    insurers_by_slug = {i.slug: i for i in db.scalars(select(Insurer))}

    created, updated, errors, warnings, imported = 0, 0, [], [], []
    for index, raw in enumerate(payload.facilities):
        external_id = str(raw.get("external_id", "")) if isinstance(raw, dict) else ""
        try:
            record = ImportFacility.model_validate(raw)
        except ValidationError as exc:
            problems = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
            errors.append({"index": index, "external_id": external_id, "error": problems})
            continue

        unknown = [s for s in record.services if s not in services_by_slug] + [i for i in record.insurers if i not in insurers_by_slug]
        if unknown:
            errors.append({"index": index, "external_id": record.external_id, "error": f"Unknown service or insurer codes: {', '.join(unknown)}"})
            continue

        services = [services_by_slug[s] for s in dict.fromkeys(record.services)]
        insurers = [insurers_by_slug[i] for i in dict.fromkeys(record.insurers)]
        facility = db.scalar(select(Facility).where(Facility.source_id == source.id, Facility.external_id == record.external_id))
        if facility is None:
            same_name = db.scalar(
                select(Facility.slug).where(func.lower(Facility.name) == record.name.lower(), func.lower(Facility.town) == record.town.lower())
            )
            if same_name:
                warnings.append({"index": index, "external_id": record.external_id, "warning": f"Possible duplicate of '{same_name}'"})
            facility = Facility(
                slug=unique_slug(db, slugify(f"{record.name} {record.town}")),
                source_id=source.id,
                external_id=record.external_id,
                is_demo=payload.is_demo,
            )
            db.add(facility)
            created += 1
        else:
            updated += 1
        _apply(facility, record, services, insurers)
        db.flush()
        imported.append({"external_id": record.external_id, "slug": facility.slug})

    batch = ImportBatch(
        source_id=source.id,
        submitted_by_user_id=submitted_by_user_id,
        received_count=len(payload.facilities),
        created_count=created,
        updated_count=updated,
        error_count=len(errors),
        errors=errors,
    )
    db.add(batch)
    db.commit()
    return {
        "batch_id": batch.id,
        "source": source.code,
        "received": len(payload.facilities),
        "created": created,
        "updated": updated,
        "failed": len(errors),
        "errors": errors,
        "warnings": warnings,
        "records": imported,
    }
