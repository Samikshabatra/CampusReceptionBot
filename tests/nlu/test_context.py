from reception.nlu.context import SessionContext, resolve
from reception.nlu.entities import Entities


def test_pronoun_fills_last_place() -> None:
    ctx = SessionContext(last_place_ids=["xerox_shop"])
    e = resolve("what are its timings", Entities(), ctx)
    assert e.place_ids == ["xerox_shop"]


def test_and_for_keeps_new_category_and_old_course() -> None:
    ctx = SessionContext(last_course_ids=["50"], last_category="karnataka")
    e = resolve("and for nri", Entities(fee_category="nri"), ctx)
    assert e.course_ids == ["50"] and e.fee_category == "nri"


def test_course_followup_after_place_question() -> None:
    ctx = SessionContext(
        last_place_ids=["xerox_shop"], last_course_ids=["50"], last_intent="course_fees"
    )
    e = resolve("and for nri", Entities(fee_category="nri"), ctx)
    assert e.course_ids == ["50"] and e.place_ids == []


def test_place_followup_after_course_question() -> None:
    ctx = SessionContext(last_place_ids=["library"], last_course_ids=["50"], last_intent="navigate")
    e = resolve("what are its timings", Entities(), ctx)
    assert e.place_ids == ["library"] and e.course_ids == []


def test_no_marker_no_fill() -> None:
    ctx = SessionContext(last_place_ids=["xerox_shop"])
    assert resolve("where is the library", Entities(place_ids=["library"]), ctx).place_ids == [
        "library"
    ]
    assert resolve("hello", Entities(), ctx).place_ids == []


def test_is_elliptical() -> None:
    assert SessionContext.is_elliptical("and for nri")
    assert SessionContext.is_elliptical("what about oci")
    assert not SessionContext.is_elliptical("mca fees")
