"""Pure CSV/Excel/vCard <-> Contact conversion — stage 4 (import/export).

Deliberately DB-agnostic: these functions only turn bytes into
`ContactImportRow`/`ImportRowError` lists (import) or `Contact` lists into
bytes (export). `app.handlers.import_export_handler` is what actually talks
to the repositories (bulk-creating contacts, linking dimension nodes).
"""

from __future__ import annotations

import io
from datetime import date
from typing import Any

import pandas as pd
import vobject
from pydantic import ValidationError

from app.models.contact import Contact
from app.models.import_result import ContactImportRow, ImportRowError

_NUMERIC_FIELDS = ("dangerous", "interesting", "difficult")
_DATE_FIELDS = ("birthday", "met_date")
# Columns that map directly onto a Contact field, as opposed to "company"/
# "tags"/"interests" — those are dimension-node links, not Contact
# properties, and go into ContactImportRow.companies/tags/interests instead.
_CONTACT_COLUMNS = (
    "name",
    "photo",
    "phone",
    "email",
    "position",
    "city",
    "birthday",
    "notes",
    "met_place",
    "met_date",
    "contact_type",
    "circle",
    "dangerous",
    "interesting",
    "difficult",
)

def _clean(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _split_list(value: Any) -> list[str]:
    text = _clean(value)
    if text is None:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def _row_to_contact_fields(row: pd.Series) -> dict[str, Any]:
    """Coerce one CSV/Excel row's known columns onto Contact's field types.

    Every column is read as text (`dtype=str` in `parse_csv`) and coerced
    explicitly here rather than trusting pandas' automatic dtype inference,
    which is inconsistent across NaN-mixed numeric/date columns (e.g. an
    int column with one blank cell silently becomes float64).
    """
    fields: dict[str, Any] = {}
    for column in _CONTACT_COLUMNS:
        if column not in row.index:
            continue
        value = _clean(row[column])
        if value is None:
            continue
        if column in _NUMERIC_FIELDS:
            fields[column] = int(float(value))
        elif column in _DATE_FIELDS:
            fields[column] = date.fromisoformat(value)
        else:
            fields[column] = value
    return fields


def parse_csv(filename: str, data: bytes) -> tuple[list[ContactImportRow], list[ImportRowError]]:
    """Parse a CSV/Excel upload (dispatched on `filename`'s extension) into
    valid rows plus per-row errors — one bad row doesn't fail the batch."""
    buffer = io.BytesIO(data)
    if filename.lower().endswith((".xlsx", ".xls")):
        frame = pd.read_excel(buffer, dtype=str)
    else:
        frame = pd.read_csv(buffer, dtype=str)

    rows: list[ContactImportRow] = []
    errors: list[ImportRowError] = []
    for position, (_, row) in enumerate(frame.iterrows(), start=2):  # row 1 is the header
        try:
            contact = Contact.model_validate(_row_to_contact_fields(row))
        except (ValidationError, ValueError) as exc:
            errors.append(ImportRowError(row=position, message=str(exc)))
            continue
        rows.append(
            ContactImportRow(
                contact=contact,
                companies=_split_list(row.get("company")),
                tags=_split_list(row.get("tags")),
                interests=_split_list(row.get("interests")),
            )
        )
    return rows, errors


def contacts_to_csv(contacts: list[Contact]) -> bytes:
    """The export half. Only Contact's own fields round-trip through
    export -> import — linked dimension data (company/tags/interests) isn't
    included here, only accepted on import, since including it would need a
    per-contact links query the CSV export path doesn't otherwise make."""
    if not contacts:
        frame = pd.DataFrame(columns=[name for name in Contact.model_fields if name != "id"])
    else:
        records = [contact.model_dump(mode="json", exclude={"id"}) for contact in contacts]
        frame = pd.DataFrame(records)
    return frame.to_csv(index=False).encode("utf-8")


# --- vCard ---

# Non-standard properties, populated only by our own contacts_to_vcard, to
# round-trip fields the vCard standard has no place for. Never expected on
# an externally-produced vCard (e.g. a phone/CardDAV export).
_X_CIRCLE = "x-circle"
_X_CONTACT_TYPE = "x-contact-type"
_X_DANGEROUS = "x-dangerous"
_X_INTERESTING = "x-interesting"
_X_DIFFICULT = "x-difficult"


def parse_vcard(data: bytes) -> tuple[list[ContactImportRow], list[ImportRowError]]:
    """Parse one or more concatenated vCards. Standard fields map onto
    Contact directly (FN->name, TEL->phone, EMAIL->email, TITLE->position,
    NOTE->notes, BDAY->birthday, ORG->company link, CATEGORIES->tags).
    Embedded binary PHOTOs are skipped — `Contact.photo` is a path/URL
    string and there's no file-storage backend yet (a stage-2 decision)."""
    text = data.decode("utf-8", errors="replace")
    rows: list[ContactImportRow] = []
    errors: list[ImportRowError] = []
    for position, card in enumerate(vobject.readComponents(text), start=1):
        try:
            fields: dict[str, Any] = {}
            if hasattr(card, "fn"):
                fields["name"] = card.fn.value
            if getattr(card, "tel_list", None):
                fields["phone"] = card.tel_list[0].value
            if getattr(card, "email_list", None):
                fields["email"] = card.email_list[0].value
            if hasattr(card, "title"):
                fields["position"] = card.title.value
            if hasattr(card, "note"):
                fields["notes"] = card.note.value
            if hasattr(card, "bday"):
                fields["birthday"] = date.fromisoformat(str(card.bday.value)[:10])
            if _X_CIRCLE in card.contents:
                fields["circle"] = card.contents[_X_CIRCLE][0].value
            if _X_CONTACT_TYPE in card.contents:
                fields["contact_type"] = card.contents[_X_CONTACT_TYPE][0].value
            for x_field, contact_field in (
                (_X_DANGEROUS, "dangerous"),
                (_X_INTERESTING, "interesting"),
                (_X_DIFFICULT, "difficult"),
            ):
                if x_field in card.contents:
                    fields[contact_field] = int(card.contents[x_field][0].value)

            contact = Contact.model_validate(fields)
        except (ValidationError, ValueError, AttributeError) as exc:
            errors.append(ImportRowError(row=position, message=str(exc)))
            continue

        companies = list(card.org.value) if getattr(card, "org", None) and card.org.value else []
        tags = list(card.categories.value) if hasattr(card, "categories") else []
        rows.append(ContactImportRow(contact=contact, companies=companies, tags=tags))
    return rows, errors


def contacts_to_vcard(contacts: list[Contact]) -> bytes:
    blob = io.StringIO()
    for contact in contacts:
        card = vobject.vCard()
        card.add("fn").value = contact.name
        card.add("n").value = vobject.vcard.Name(given=contact.name)
        if contact.phone:
            card.add("tel").value = contact.phone
        if contact.email:
            card.add("email").value = contact.email
        if contact.position:
            card.add("title").value = contact.position
        if contact.notes:
            card.add("note").value = contact.notes
        if contact.birthday:
            card.add("bday").value = contact.birthday.isoformat()
        if contact.circle:
            card.add(_X_CIRCLE).value = contact.circle.value
        if contact.contact_type:
            card.add(_X_CONTACT_TYPE).value = contact.contact_type.value
        if contact.dangerous is not None:
            card.add(_X_DANGEROUS).value = str(contact.dangerous)
        if contact.interesting is not None:
            card.add(_X_INTERESTING).value = str(contact.interesting)
        if contact.difficult is not None:
            card.add(_X_DIFFICULT).value = str(contact.difficult)
        blob.write(card.serialize())
    return blob.getvalue().encode("utf-8")
