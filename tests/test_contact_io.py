"""Unit tests for `app.services.contact_io` — pure CSV/Excel/vCard <-> Contact
conversion, no Neo4j needed."""

from __future__ import annotations

from datetime import date

from app.models.contact import Contact
from app.models.enums import Circle, ContactType
from app.services.contact_io import contacts_to_csv, contacts_to_vcard, parse_csv, parse_vcard


def test_parse_csv_valid_rows_with_dimension_links() -> None:
    csv_bytes = (
        b"name,phone,email,birthday,contact_type,circle,dangerous,company,tags\n"
        b"Ada Lovelace,+1-555-0100,ada@example.com,1815-12-10,connector,support_circle,3,"
        b"Acme Inc,\"vip, mathematician\"\n"
    )

    rows, errors = parse_csv("import.csv", csv_bytes)

    assert errors == []
    assert len(rows) == 1
    row = rows[0]
    assert row.contact.name == "Ada Lovelace"
    assert row.contact.phone == "+1-555-0100"
    assert row.contact.birthday == date(1815, 12, 10)
    assert row.contact.contact_type == ContactType.CONNECTOR
    assert row.contact.circle == Circle.SUPPORT_CIRCLE
    assert row.contact.dangerous == 3
    assert row.companies == ["Acme Inc"]
    assert row.tags == ["vip", "mathematician"]


def test_parse_csv_reports_row_level_errors_without_failing_the_batch() -> None:
    csv_bytes = (
        b"name,dangerous\nValid Person,5\n,11\n"  # row 2: missing name; row 3: dangerous > 10
    )

    rows, errors = parse_csv("import.csv", csv_bytes)

    assert len(rows) == 1
    assert rows[0].contact.name == "Valid Person"
    assert len(errors) == 1
    assert errors[0].row == 3  # 1-indexed, header is row 1


def test_contacts_to_csv_round_trips_through_parse_csv() -> None:
    original = Contact(
        name="Grace Hopper",
        phone="+1-555-9999",
        birthday=date(1906, 12, 9),
        circle=Circle.FUNCTIONAL_CIRCLES,
        interesting=8,
    )

    csv_bytes = contacts_to_csv([original])
    rows, errors = parse_csv("export.csv", csv_bytes)

    assert errors == []
    assert len(rows) == 1
    round_tripped = rows[0].contact
    assert round_tripped.name == original.name
    assert round_tripped.phone == original.phone
    assert round_tripped.birthday == original.birthday
    assert round_tripped.circle == original.circle
    assert round_tripped.interesting == original.interesting


def test_contacts_to_csv_empty_list_still_has_a_header() -> None:
    csv_bytes = contacts_to_csv([])
    assert b"name" in csv_bytes.splitlines()[0]


def test_parse_vcard_standard_fields() -> None:
    vcard_bytes = (
        b"BEGIN:VCARD\r\n"
        b"VERSION:3.0\r\n"
        b"FN:Alan Turing\r\n"
        b"TEL:+1-555-1111\r\n"
        b"EMAIL:alan@example.com\r\n"
        b"TITLE:Mathematician\r\n"
        b"ORG:Bletchley Park\r\n"
        b"NOTE:Codebreaker\r\n"
        b"BDAY:1912-06-23\r\n"
        b"CATEGORIES:legend,cryptography\r\n"
        b"END:VCARD\r\n"
    )

    rows, errors = parse_vcard(vcard_bytes)

    assert errors == []
    assert len(rows) == 1
    row = rows[0]
    assert row.contact.name == "Alan Turing"
    assert row.contact.phone == "+1-555-1111"
    assert row.contact.email == "alan@example.com"
    assert row.contact.position == "Mathematician"
    assert row.contact.notes == "Codebreaker"
    assert row.contact.birthday == date(1912, 6, 23)
    assert row.companies == ["Bletchley Park"]
    assert row.tags == ["legend", "cryptography"]


def test_contacts_to_vcard_round_trips_our_own_extension_fields() -> None:
    """The X-* fields (circle/contact_type/dangerous/interesting/difficult)
    only exist so our own export -> import round-trips losslessly — no
    standard vCard property covers them."""
    original = Contact(
        name="Marie Curie",
        contact_type=ContactType.INSIDER,
        circle=Circle.SUCCESS_CIRCLE,
        dangerous=2,
        interesting=10,
        difficult=4,
    )

    vcard_bytes = contacts_to_vcard([original])
    rows, errors = parse_vcard(vcard_bytes)

    assert errors == []
    assert len(rows) == 1
    round_tripped = rows[0].contact
    assert round_tripped.name == original.name
    assert round_tripped.contact_type == original.contact_type
    assert round_tripped.circle == original.circle
    assert round_tripped.dangerous == original.dangerous
    assert round_tripped.interesting == original.interesting
    assert round_tripped.difficult == original.difficult


def test_contacts_to_vcard_concatenates_multiple_cards() -> None:
    contacts = [Contact(name="Alice"), Contact(name="Bob")]
    vcard_bytes = contacts_to_vcard(contacts)
    rows, errors = parse_vcard(vcard_bytes)

    assert errors == []
    assert [row.contact.name for row in rows] == ["Alice", "Bob"]
