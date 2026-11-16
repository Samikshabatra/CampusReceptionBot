from pathlib import Path

import pytest

from reception.copy import (
    CALENDAR_EXPIRED,
    CLARIFY,
    FACULTY_LINE,
    HANDOVER_LINE,
    OUT_OF_SCOPE,
    REPROMPT,
    ROOM_NOT_FOUND,
    UNVERIFIED_SUFFIX,
)
from reception.dialogue.router import Assistant
from reception.engines.navigation import build_graph
from reception.kb.loader import KnowledgeBase
from reception.llm.base import FakeLLM
from reception.nlu.context import SessionContext
from tests.conftest import dt

NOW = dt("2026-11-04 10:00")


@pytest.fixture()
def assistant(kb: KnowledgeBase, classifier, index) -> Assistant:  # type: ignore[no-untyped-def]
    from reception.config import load_config

    cfg = load_config(Path("configs/app.yaml"))
    return Assistant(kb, cfg, classifier, index, FakeLLM([]), build_graph(kb, cfg))


def ask(a: Assistant, text: str, ctx: SessionContext | None = None, now=NOW):  # type: ignore[no-untyped-def]
    return a.handle(text, ctx or SessionContext(), now)


def test_xerox_then_timings(assistant: Assistant) -> None:
    ctx = SessionContext()
    r1 = ask(assistant, "Where is the zerox shop?", ctx)
    assert r1.intent == "navigate" and r1.card.data["floors"] == ["G", "B"]
    r2 = ask(assistant, "what are its timings?", ctx)
    assert r2.intent == "facility_hours" and r2.speech.endswith(UNVERIFIED_SUFFIX.strip())


def test_room_806_not_on_map(assistant: Assistant) -> None:
    r = ask(assistant, "Where is Room 806?")
    assert r.speech == ROOM_NOT_FOUND.format(room="806") and r.handover_reason == "room_not_found"


def test_room_812(assistant: Assistant) -> None:
    assert ask(assistant, "where is room 812").card.data["targets"] == ["room_812"]


def test_commerce_not_in_block(assistant: Assistant) -> None:
    assert "isn't in Central Block" in ask(assistant, "where is the commerce department").speech


def test_nearest_washroom(assistant: Assistant) -> None:
    r = ask(assistant, "where is the washroom")
    assert r.card.kind == "map" and r.card.data["floors"] == ["G", "2"]


def test_fees_followup(assistant: Assistant) -> None:
    ctx = SessionContext()
    assert "2 lakh 42 thousand rupees" in ask(assistant, "MCA fees", ctx).speech
    assert "NRI" in ask(assistant, "and for NRI?", ctx).speech


def test_ambiguous_course_clarifies(assistant: Assistant) -> None:
    r = ask(assistant, "fees for msc ai and ml")
    assert r.card.kind == "clarify" and len(r.card.data["options"]) == 2


def test_urgent(assistant: Assistant) -> None:
    r = ask(assistant, "I feel unwell")
    assert r.handover_reason == "urgent" and "Basement" in r.speech


def test_human(assistant: Assistant) -> None:
    assert ask(assistant, "I want to talk to a person").handover_reason == "human"


def test_faculty(assistant: Assistant) -> None:
    assert ask(assistant, "where is professor sharma").speech == FACULTY_LINE


def test_out_of_scope(assistant: Assistant) -> None:
    assert ask(assistant, "what's the weather today").speech == OUT_OF_SCOPE


@pytest.mark.parametrize("text", ["", "   ", "x" * 2000, "???"])
def test_degenerate_input(assistant: Assistant, text: str) -> None:
    assert ask(assistant, text).speech in (REPROMPT, OUT_OF_SCOPE, HANDOVER_LINE, CLARIFY)


def test_two_misses_handover(assistant: Assistant) -> None:
    ctx = SessionContext()
    first = ask(assistant, "blorp fizzle wug", ctx)
    assert first.card.kind == "clarify"
    assert ask(assistant, "snorf glimble prax", ctx).handover_reason == "low_confidence"


def test_complaint_counts_as_miss(assistant: Assistant) -> None:
    ctx = SessionContext()
    ask(assistant, "that's wrong", ctx)
    assert ask(assistant, "not helpful", ctx).handover_reason == "low_confidence"


def test_stairs_route(assistant: Assistant) -> None:
    r = ask(assistant, "how do I get to the library by stairs")
    assert any("stairs" in n for n in r.card.data["legs"][0]["node_ids"])


def test_college_open_third_saturday(assistant: Assistant) -> None:
    s = ask(assistant, "is the college open today", now=dt("2027-01-16 10:00")).speech.lower()
    assert "library" in s


def test_calendar_expired(assistant: Assistant) -> None:
    assert ask(assistant, "library timings", now=dt("2027-06-05 10:00")).speech == CALENDAR_EXPIRED


def test_course_list(assistant: Assistant) -> None:
    r = ask(assistant, "which courses are available in computer science")
    assert r.card.kind == "course_list" and len(r.card.data["items"]) == 9


def test_admissions(assistant: Assistant) -> None:
    r = ask(assistant, "how do I apply for admission")
    assert "11 December" in r.speech and any(link.url.startswith("tel:") for link in r.links)


def test_named_event(assistant: Assistant) -> None:
    assert "27 May" in ask(assistant, "when is convocation").speech


def test_open_day(assistant: Assistant) -> None:
    assert "21 November" in ask(assistant, "when is the open day").speech


def test_contact(assistant: Assistant) -> None:
    assert "plus 9 1" in ask(assistant, "what is the reception phone number").speech


def test_library_intent(assistant: Assistant) -> None:
    r = ask(assistant, "library website")
    assert any("library.christuniversity.in" in link.url for link in r.links)


def test_repeat(assistant: Assistant) -> None:
    ctx = SessionContext()
    first = ask(assistant, "where is the library", ctx)
    assert ask(assistant, "say that again", ctx).speech == first.speech


def test_greeting_and_bye(assistant: Assistant) -> None:
    ctx = SessionContext()
    assert "Central Block" in ask(assistant, "hello", ctx).speech
    ask(assistant, "thank you, bye", ctx)
    assert ctx.ended


def test_course_info_falls_back_without_llm(assistant: Assistant) -> None:
    r = ask(assistant, "what is the MCA programme about")
    assert r.intent == "course_info" and r.handover_reason is None and "postgraduate" in r.speech


@pytest.mark.parametrize(
    "text",
    [
        "Where is the xerox shop?",
        "MCA fees",
        "Is the library open now?",
        "When is the open day?",
        "where is professor sharma",
        "how do I apply for admission",
        "where is room 1004",
        "what is the reception phone number",
        "is the college open today",
        "hello",
    ],
)
def test_speech_limits(assistant: Assistant, text: str) -> None:
    s = ask(assistant, text).speech
    assert len(s.split()) <= 40 and "http" not in s


def test_unknown_course_fact_hands_over(assistant: Assistant) -> None:
    r = ask(assistant, "how many seats are there in MCA")
    assert r.speech == HANDOVER_LINE and r.handover_reason is not None


def test_low_confidence_backed_by_place(assistant: Assistant) -> None:
    r = ask(assistant, "is the reception open", now=dt("2026-11-04 13:30"))
    assert r.intent == "facility_hours" and "lunch" in r.speech


def test_how_much_after_course_is_fee(assistant: Assistant) -> None:
    ctx = SessionContext()
    ask(assistant, "tell me about mca", ctx)
    assert "2 lakh 42 thousand rupees" in ask(assistant, "how much is it", ctx).speech


@pytest.mark.parametrize(
    "text",
    [
        "what is the placement rate for mca",
        "average salary package after bca",
        "how many seats in bca",
        "what are the hostel fees",
        "what is the timetable for mca first year",
        "cutoff for bca admission",
    ],
)
def test_topics_not_in_knowledge_hand_over(assistant: Assistant, text: str) -> None:
    r = ask(assistant, text)
    assert r.handover_reason == "not_in_knowledge" and r.speech == HANDOVER_LINE


def test_placement_office_still_navigates(assistant: Assistant) -> None:
    assert ask(assistant, "where is the placement office").card.data["targets"] == [
        "placement_office_law"
    ]


LIB = "https://library.christuniversity.in/christ_library/index.php"


@pytest.mark.parametrize(
    "text,phrase",
    [
        ("How can we issue books in the library?", "issue or borrow books"),
        ("can I borrow books", "issue or borrow books"),
        ("how do I renew a book", "renew a book"),
        ("how do I get a library card", "get library membership"),
        ("does the library have e journals", "access e-resources"),
        ("library rules", "library website"),
    ],
)
def test_library_questions_point_to_website(assistant: Assistant, text: str, phrase: str) -> None:
    r = ask(assistant, text)
    assert r.intent == "library" and phrase in r.speech and "library website" in r.speech
    assert any(link.url == LIB for link in r.links) and r.card.data["library_link"] == LIB
    assert "closed now" not in r.speech.lower() and len(r.speech.split()) <= 40


def test_library_hours_still_hours_with_link(assistant: Assistant) -> None:
    r = ask(assistant, "is the library open now")
    assert r.card.kind == "timings" and any(link.url == LIB for link in r.links)
