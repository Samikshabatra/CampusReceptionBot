"""The dialogue core: understand one utterance and route it to the right answer."""

import re
from datetime import datetime
from typing import get_args

import networkx as nx

from reception.config import AppConfig
from reception.copy import (
    ASK_PLACE,
    ASK_PROGRAMME,
    BYE_LINE,
    CLARIFY,
    GREETING_BODY,
    HUMAN_LINE,
    LIFT_LINE,
    NOT_IN_BLOCK,
    OUT_OF_SCOPE,
    PLACE_OPTIONS,
    PROGRAMME_OPTIONS,
    QUICK_OPTIONS,
    REPROMPT,
    ROOM_NOT_FOUND,
    SMALLTALK_LINE,
)
from reception.dialogue.handover import handover_response
from reception.engines.courses import (
    course_fees_response,
    course_info_response,
    course_list_response,
    speech_name,
)
from reception.engines.info import (
    admissions_response,
    college_open_response,
    contact_response,
    event_lookup_response,
    events_response,
    faculty_response,
    hours_response,
    library_response,
    library_topic,
)
from reception.engines.navigation import navigation_response, nearest_of_category
from reception.kb.loader import KnowledgeBase
from reception.llm.base import LLM, LLMUnavailable
from reception.nlu.context import SessionContext, resolve
from reception.nlu.entities import Entities, extract_entities
from reception.nlu.intent import IntentClassifier
from reception.nlu.normalise import normalise
from reception.rag.answer import rag_answer
from reception.rag.index import HybridIndex
from reception.types import Card, IntentName, Response

ALL_INTENTS: tuple[str, ...] = get_args(IntentName)
_REUSABLE = {"course_fees", "course_info", "facility_hours", "navigate"}
_COURSE_INTENTS = {"course_fees", "course_info", "course_list"}
_NOT_IN_KNOWLEDGE = re.compile(
    r"\b(placement (rate|record|percentage|statistics|drive)|placements? record|salary|salaries|"
    r"package|seats?|intake|hostel|syllabus|timetable|time table|cut ?off|ranking|"
    r"results? (announced|date|declared)|attendance|dress code|parking|college bus|bus timings|"
    r"transport|wifi|wi fi|recruit\w*|vice chancellor|principal)\b"
)
_HOURS_WORDS = re.compile(r"\b(open|opens|close|closes|closed|timings?|hours|time|when)\b")
_LIBRARY_WORD = re.compile(r"\b(library|libary|librery|books?)\b")
_FEE_WORDS = re.compile(r"\b(how much|cost|costs|fee|fees|price|charges)\b")
_COMPLAINT = re.compile(
    r"\b(that s wrong|thats wrong|wrong answer|not helpful|useless|incorrect)\b"
)
_CONTENT_WORDS = re.compile(
    r"\b(about|learn|cover|covers|syllabus|curriculum|subjects|career|scope|describe|explain)\b"
)
_LEVELS = (
    ("PhD", r"\b(phd|doctoral|doctorate)\b"),
    ("PG", r"\b(pg|postgraduate|post graduate|masters?)\b"),
    ("UG", r"\b(ug|undergraduate|under graduate|bachelors?|after 12th)\b"),
)
_INTENT_PROMPT = (
    "Classify the visitor's message for a university reception kiosk. Reply with exactly one "
    "label from this list and nothing else: {labels}, or unknown."
)


def _greeting(now: datetime) -> str:
    hello = (
        "Good morning!"
        if now.hour < 12
        else "Good afternoon!" if now.hour < 17 else "Good evening!"
    )
    return f"{hello} {GREETING_BODY}"


def _text(speech: str, intent: IntentName, conf: float, **data: object) -> Response:
    return Response(
        speech=speech, card=Card(kind="text", data={"text": speech, **data}), intent=intent,
        confidence=conf,
    )  # fmt: skip


def _clarify(speech: str, options: list[str], intent: IntentName, conf: float) -> Response:
    return Response(
        speech=speech,
        card=Card(kind="clarify", data={"options": options}),
        intent=intent,
        confidence=conf,
    )


class Assistant:
    """Understands an utterance and returns one Response."""

    def __init__(
        self,
        kb: KnowledgeBase,
        cfg: AppConfig,
        classifier: IntentClassifier,
        index: HybridIndex | None,
        llm: LLM,
        graph: nx.Graph,
    ) -> None:
        """Wire the assistant's parts together."""
        self.kb = kb
        self.cfg = cfg
        self.classifier = classifier
        self.index = index
        self.llm = llm
        self.graph = graph

    # ---------------------------------------------------------------- public
    def greet(self, ctx: SessionContext, now: datetime) -> Response:
        """Opening line when a visitor walks up (no button press needed)."""
        r = _clarify(_greeting(now), list(QUICK_OPTIONS), "greeting", 1.0)
        ctx.turns.append(("", r))
        ctx.last_intent = "greeting"
        return r

    def handle(self, text: str, ctx: SessionContext, now: datetime) -> Response:
        """Answer one utterance and update the session.

        Args:
            text: Typed or transcribed visitor text.
            ctx: Session context (mutated).
            now: Current time (Asia/Kolkata).

        Returns:
            The response to speak and show.
        """
        norm = normalise(text, self.cfg.max_input_chars)
        if not norm:
            return _clarify(REPROMPT, list(QUICK_OPTIONS), "repeat", 0.0)
        if _COMPLAINT.search(norm):
            return self._miss(ctx, "repeat", 0.0)
        ents = resolve(norm, extract_entities(norm, self.kb, self.cfg.fuzzy_threshold), ctx)
        intent, conf = self.classifier.predict(text[: self.cfg.max_input_chars])
        if SessionContext.is_elliptical(norm) and ctx.last_intent in _REUSABLE:
            intent, conf = ctx.last_intent, max(conf, self.cfg.intent_threshold)
        if ents.room and intent in ("out_of_scope", "smalltalk", "repeat"):
            intent = "navigate"
        if (
            _LIBRARY_WORD.search(norm)
            and library_topic(norm)
            and not _HOURS_WORDS.search(norm)
            and not (ents.room or ents.category_request)
        ):
            intent, conf = "library", max(conf, self.cfg.intent_threshold)
        if _NOT_IN_KNOWLEDGE.search(norm) and intent != "library":
            # Topics the verified knowledge does not cover: never answer something adjacent.
            response = handover_response(self.kb, "not_in_knowledge", intent, conf)
            self._remember(ctx, text, ents, response)
            return response
        threshold = self.cfg.intent_threshold
        if ents.course_ids and _FEE_WORDS.search(norm):
            intent, conf = "course_fees", max(conf, threshold)  # known programme + fee word
        backed = ((ents.place_ids or ents.room) and intent in ("navigate", "facility_hours")) or (
            ents.course_ids and intent in _COURSE_INTENTS
        )
        if backed and conf < threshold:
            conf = threshold  # the recognised place/course corroborates the guess
        unclear = intent in ("out_of_scope", "smalltalk") or conf < self.cfg.intent_threshold
        if len(ents.course_ids) == 1 and unclear:
            # A question about a known programme that we have no field for: answer only
            # if the passages support it, otherwise hand over (never "out of scope").
            response = self._grounded_only(text, ents.course_ids[0], conf)
            self._remember(ctx, text, ents, response)
            return response
        if conf < self.cfg.intent_threshold:
            fallback = self._llm_intent(text)
            if fallback is None:
                return self._miss(ctx, intent, conf)
            intent = fallback
        ctx.misunderstandings = 0
        response = self._dispatch(intent, conf, text, norm, ents, ctx, now)
        self._remember(ctx, text, ents, response)
        return response

    # --------------------------------------------------------------- helpers
    def _grounded_only(self, text: str, course_id: str, conf: float) -> Response:
        if self.index is None:
            return handover_response(self.kb, "retrieval_gate", "course_info", conf)
        question = f"{text} ({self.kb.courses[course_id].name})"
        return rag_answer(question, self.kb, self.index, self.llm, self.cfg, "course_info", conf)

    def _miss(self, ctx: SessionContext, intent: IntentName, conf: float) -> Response:
        ctx.misunderstandings += 1
        if ctx.misunderstandings >= 2:
            ctx.misunderstandings = 0
            return handover_response(self.kb, "low_confidence", intent, conf)
        return _clarify(CLARIFY, list(QUICK_OPTIONS), intent, conf)

    def _llm_intent(self, text: str) -> IntentName | None:
        try:
            reply = self.llm.complete(
                _INTENT_PROMPT.format(labels=", ".join(ALL_INTENTS)), text[:500]
            )
        except LLMUnavailable:
            return None
        label = reply.strip().strip(".").lower()
        return label if label in ALL_INTENTS else None  # type: ignore[return-value]

    def _remember(self, ctx: SessionContext, text: str, ents: Entities, r: Response) -> None:
        if r.intent != "repeat":
            ctx.turns.append((text, r))
        if r.card.kind == "map" and r.card.data.get("targets"):
            ctx.last_place_ids = [r.card.data["targets"][0]]
        elif ents.place_ids:
            ctx.last_place_ids = ents.place_ids[:1]
        if ents.course_ids and r.card.kind != "clarify":
            ctx.last_course_ids = ents.course_ids
        if ents.fee_category:
            ctx.last_category = ents.fee_category
        if ents.department:
            ctx.last_department = ents.department
        ctx.last_intent = r.intent

    def _dispatch(
        self,
        intent: IntentName,
        conf: float,
        text: str,
        norm: str,
        e: Entities,
        ctx: SessionContext,
        now: datetime,
    ) -> Response:
        kb = self.kb
        if intent == "navigate":
            return self._navigate(e, conf)
        if intent == "facility_hours":
            target = (
                e.place_ids[0] if e.place_ids else ("library" if "library" in norm else "offices")
            )
            return hours_response(kb, target, now, conf)
        if intent == "college_open":
            return college_open_response(kb, now, conf)
        if intent in ("course_info", "course_fees"):
            return self._course(intent, conf, text, norm, e)
        if intent == "course_list":
            level = next((lv for lv, pat in _LEVELS if re.search(pat, norm)), None)
            return course_list_response(kb, e.department, level, conf)
        if intent == "admissions":
            return admissions_response(kb, now.date(), conf)
        if intent == "contact":
            topic = (
                "admissions"
                if "admission" in norm
                else "library" if "library" in norm else "general"
            )
            return contact_response(kb, topic, conf)  # type: ignore[arg-type]
        if intent == "faculty":
            return faculty_response(kb, self.graph, self.cfg, e.department, conf)
        if intent == "events":
            named = event_lookup_response(kb, now.date(), norm, conf)
            if named:
                return named
            if re.search(r"\bholiday", norm):
                return events_response(kb, now.date(), "holidays", conf)
            if re.search(r"\b(admission|interview)", norm):
                return events_response(kb, now.date(), "admissions", conf)
            if re.search(r"\b(open day|daksh)\b", norm):
                return events_response(kb, now.date(), "open_day", conf)
            return events_response(kb, now.date(), "upcoming", conf)
        if intent == "library":
            if _HOURS_WORDS.search(norm):
                hours = hours_response(kb, "library", now, conf)
                hours.intent = "library"
                return hours
            return library_response(kb, norm, conf)
        if intent == "human":
            return handover_response(kb, "human", intent, conf, HUMAN_LINE)
        if intent == "urgent":
            return handover_response(kb, "urgent", intent, conf)
        if intent == "greeting":
            return _clarify(_greeting(now), list(QUICK_OPTIONS), intent, conf)
        if intent == "thanks_bye":
            ctx.ended = True
            return _text(BYE_LINE, intent, conf)
        if intent == "repeat":
            last = ctx.last_response
            return last if last else _clarify(REPROMPT, list(QUICK_OPTIONS), intent, conf)
        if intent == "smalltalk":
            return _text(SMALLTALK_LINE, intent, conf)
        return _text(OUT_OF_SCOPE, "out_of_scope", conf)

    def _navigate(self, e: Entities, conf: float) -> Response:
        kb = self.kb
        prefer = "stairs" if e.prefer_stairs else self.cfg.route_preference
        if e.room:
            pid = f"room_{e.room.lower()}"
            if pid not in kb.places:
                speech = ROOM_NOT_FOUND.format(room=e.room.upper())
                return handover_response(kb, "room_not_found", "navigate", conf, speech)
            return navigation_response(kb, self.graph, self.cfg, [pid], prefer, conf)
        if e.place_ids:
            return navigation_response(kb, self.graph, self.cfg, e.place_ids, prefer, conf)
        if e.category_request in ("washroom", "water"):
            p = nearest_of_category(kb, self.graph, self.cfg.kiosk_node, e.category_request)
            return navigation_response(kb, self.graph, self.cfg, [p.id], prefer, conf)
        if e.category_request == "lift":
            return _text(LIFT_LINE, "navigate", conf)
        if e.department:
            target = kb.departments.get(e.department, "not_in_central_block")
            if target == "not_in_central_block":
                speech = NOT_IN_BLOCK.format(department=e.department)
                return handover_response(kb, "not_in_block", "navigate", conf, speech)
            return navigation_response(kb, self.graph, self.cfg, [target], prefer, conf)
        return _clarify(ASK_PLACE, list(PLACE_OPTIONS), "navigate", conf)

    def _course(
        self, intent: IntentName, conf: float, text: str, norm: str, e: Entities
    ) -> Response:
        kb = self.kb
        if len(e.course_ids) > 1:
            names = [speech_name(kb.courses[c].name) for c in e.course_ids]
            return _clarify("Which one do you mean?", names, intent, conf)
        if not e.course_ids:
            if intent == "course_info" and e.department:
                return course_list_response(kb, e.department, None, conf)
            if intent == "course_info" and self.index is not None:
                return rag_answer(text, kb, self.index, self.llm, self.cfg, intent, conf)
            return _clarify(ASK_PROGRAMME, list(PROGRAMME_OPTIONS), intent, conf)
        cid = e.course_ids[0]
        if intent == "course_fees":
            return course_fees_response(kb, cid, e.fee_category, e.year, conf)
        if _CONTENT_WORDS.search(norm) and self.index is not None and kb.courses[cid].description:
            question = f"{text} ({kb.courses[cid].name})"
            r = rag_answer(question, kb, self.index, self.llm, self.cfg, intent, conf)
            if r.handover_reason is None:
                return r
        return course_info_response(kb, cid, conf)
