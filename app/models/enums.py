"""Fixed enums resolved in networking-app-ai-prompt.md.

Every value here traces back to an explicit answer in that document —
nothing here is invented. Where the spec didn't fix a set of values (e.g.
the `type` on a KNOWS relationship, or a relative's `relation_type`), the
corresponding model field stays a free-form ``str`` instead of an enum.
"""

from __future__ import annotations

from enum import StrEnum


class Circle(StrEnum):
    """The 3 concentric "FC SC SC" zones (item 1). Full names only — never
    abbreviated, since Support Circle and Success Circle both shorten to
    "SC"."""

    SUPPORT_CIRCLE = "support_circle"  # core / innermost zone
    FUNCTIONAL_CIRCLES = "functional_circles"  # middle layer
    SUCCESS_CIRCLE = "success_circle"  # outer zone


class ContactType(StrEnum):
    """Exactly one value per contact (item 2)."""

    CONNECTOR = "connector"
    CONDENSER = "condenser"
    BRIDGE = "bridge"
    INSIDER = "insider"


class InteractionType(StrEnum):
    """Kinds of `(:Contact)-[:HAD_INTERACTION]->(:Interaction)` events, as
    listed in the spec description (meetings/calls/correspondence/referrals)."""

    MEETING = "meeting"
    CALL = "call"
    CORRESPONDENCE = "correspondence"
    REFERRAL = "referral"


class DimensionLinkType(StrEnum):
    """The property-less `(:Contact)-[REL]->(:DimensionNode)` relationship
    types from the graph model — everything except KNOWS/HAD_INTERACTION/
    NEXT_ACTION/HAS_RELATIVE, which carry properties or create a new node
    and so get their own dedicated endpoints instead."""

    WORKS_AT = "WORKS_AT"
    ATTENDED = "ATTENDED"
    MEMBER_OF = "MEMBER_OF"
    INVOLVED_IN = "INVOLVED_IN"
    INTERESTED_IN = "INTERESTED_IN"
    TAGGED = "TAGGED"


class ActionType(StrEnum):
    """`(:Contact)-[:NEXT_ACTION]->(:Action)` types, as listed in the spec
    description (write/call/meet/come back later)."""

    WRITE = "write"
    CALL = "call"
    MEET = "meet"
    FOLLOW_UP_LATER = "follow_up_later"
