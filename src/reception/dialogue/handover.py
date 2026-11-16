"""Hand the visitor over to a human, with contacts on screen."""

from reception.copy import HANDOVER_LINE, URGENT_LINE
from reception.kb.loader import KnowledgeBase
from reception.kb.models import Contact
from reception.types import Card, IntentName, Link, Response


def contact_link(c: Contact) -> Link:
    """A tel:/mailto:/https link for a contact."""
    if c.kind == "phone":
        return Link(label=f"{c.label}: {c.value}", url="tel:" + c.value.replace(" ", ""))
    if c.kind == "email":
        return Link(label=f"{c.label}: {c.value}", url=f"mailto:{c.value}")
    return Link(label=c.label, url=c.value)


def contact_items(kb: KnowledgeBase, topics: tuple[str, ...]) -> list[Contact]:
    """Contacts for the given topics, in file order."""
    return [c for c in kb.contacts if c.topic in topics]


def handover_response(
    kb: KnowledgeBase,
    reason: str,
    intent: IntentName,
    confidence: float,
    speech: str = HANDOVER_LINE,
) -> Response:
    """Controlled reply + reception contacts.

    Args:
        kb: Knowledge base.
        reason: Why (e.g. ``verify_failed``, ``urgent``, ``room_not_found``).
        intent: Intent being answered.
        confidence: Intent confidence.
        speech: What to say; ``urgent`` always uses the urgent line.

    Returns:
        A ``handover`` card response.
    """
    contacts = contact_items(kb, ("general", "admissions"))
    data: dict[str, object] = {
        "reason": reason,
        "contacts": [c.model_dump() for c in contacts],
    }
    if reason == "urgent":
        speech = URGENT_LINE
        data["place_ids"] = ["health_centre"]
    return Response(
        speech=speech,
        card=Card(kind="handover", data=data),
        links=[contact_link(c) for c in contacts],
        verified=True,
        intent=intent,
        confidence=confidence,
        handover_reason=reason,
    )
