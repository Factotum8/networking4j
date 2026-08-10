"""Human-readable display labels for enum values, shared across pages.

`Circle`/`ContactType` values are kept in their exact spec-mandated English
form (item 1 in networking-app-ai-prompt.md: "Full names are used
everywhere in code/UI... never the 'SC' abbreviation") — these are named
concepts from the book the app is based on, not generic words, so they
aren't translated. `ActionType`/`InteractionType`/`DimensionLinkType` are
plain descriptive terms the spec never asked to be kept in English, so
those get Russian labels for the UI chrome, matching how this project's
sessions are conducted.
"""

from __future__ import annotations

from app.models.enums import ActionType, Circle, ContactType, DimensionLinkType, InteractionType

CIRCLE_LABELS: dict[Circle, str] = {
    Circle.SUPPORT_CIRCLE: "Support Circle",
    Circle.FUNCTIONAL_CIRCLES: "Functional Circles",
    Circle.SUCCESS_CIRCLE: "Success Circle",
}

CONTACT_TYPE_LABELS: dict[ContactType, str] = {
    ContactType.CONNECTOR: "Connector",
    ContactType.CONDENSER: "Condenser",
    ContactType.BRIDGE: "Bridge",
    ContactType.INSIDER: "Insider",
}

ACTION_TYPE_LABELS: dict[ActionType, str] = {
    ActionType.WRITE: "Написать",
    ActionType.CALL: "Позвонить",
    ActionType.MEET: "Встретиться",
    ActionType.FOLLOW_UP_LATER: "Вернуться позже",
}

INTERACTION_TYPE_LABELS: dict[InteractionType, str] = {
    InteractionType.MEETING: "Встреча",
    InteractionType.CALL: "Звонок",
    InteractionType.CORRESPONDENCE: "Переписка",
    InteractionType.REFERRAL: "Рекомендация",
}

DIMENSION_TYPE_LABELS: dict[DimensionLinkType, str] = {
    DimensionLinkType.WORKS_AT: "Компании",
    DimensionLinkType.ATTENDED: "События",
    DimensionLinkType.MEMBER_OF: "Сообщества",
    DimensionLinkType.INVOLVED_IN: "Проекты",
    DimensionLinkType.INTERESTED_IN: "Интересы",
    DimensionLinkType.TAGGED: "Теги",
}
