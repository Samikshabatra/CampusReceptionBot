import pytest

from reception.kb.loader import KnowledgeBase
from reception.nlu.entities import Entities, extract_entities
from reception.nlu.normalise import normalise


def ents(text: str, kb: KnowledgeBase) -> Entities:
    return extract_entities(normalise(text, 500), kb, 80)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Where is Room 806?", "where is room 806"),
        ("where is room eight zero six", "where is room 806"),
        ("eight oh six", "806"),
        ("eight hundred and twelve", "812"),
        ("ten zero four", "1004"),
        ("one thousand", "1000"),
        ("fees for year two", "fees for year 2"),
    ],
)
def test_normalise(text: str, expected: str) -> None:
    assert normalise(text, 500) == expected


def test_truncation() -> None:
    assert len(normalise("a" * 2000, 500)) == 500


@pytest.mark.parametrize(
    "text,room",
    [
        ("where is room eight zero six", "806"),
        ("Room 806?", "806"),
        ("eight hundred and twelve", "812"),
        ("c101 please", "c101"),
        ("room 1000", "1000"),
    ],
)
def test_rooms(text: str, room: str, kb: KnowledgeBase) -> None:
    assert ents(text, kb).room == room


def test_year_number_not_room(kb: KnowledgeBase) -> None:
    assert ents("fees for 2027", kb).room is None


@pytest.mark.parametrize(
    "text",
    ["where is the zerox shop", "were is zerox", "I need a photocopy", "print shop", "xerox"],
)
def test_xerox_aliases(text: str, kb: KnowledgeBase) -> None:
    assert ents(text, kb).place_ids == ["xerox_shop"]


def test_libary_typo(kb: KnowledgeBase) -> None:
    assert ents("libary timing", kb).place_ids == ["library"]


@pytest.mark.parametrize(
    "text,pid",
    [
        ("where can I get coffee", "ccd"),
        ("canteen", "gourmet"),
        ("health centre", "health_centre"),
        ("mca lab", "mca_lab"),
        ("accounts office", "accounts_office"),
        ("where is the admissions office", "admissions_office"),
        ("faculty lounge", "faculty_staff_room"),
    ],
)
def test_places(text: str, pid: str, kb: KnowledgeBase) -> None:
    assert pid in ents(text, kb).place_ids


def test_no_place_in_unrelated_text(kb: KnowledgeBase) -> None:
    assert ents("what is the weather today", kb).place_ids == []


def test_partial_alias_word_does_not_match(kb: KnowledgeBase) -> None:
    assert ents("where is the office", kb).place_ids == []


def test_hod_and_documents(kb: KnowledgeBase) -> None:
    assert ents("where is the placement office for law", kb).place_ids == ["placement_office_law"]
    assert ents("exam section", kb).place_ids == ["office_accounts_exams"]
    assert ents("where do I submit documents", kb).place_ids == ["office_processing_im"]


def test_course_and_category(kb: KnowledgeBase) -> None:
    e = ents("MCA fees for NRI second year", kb)
    assert e.course_ids == ["50"] and e.fee_category == "nri" and e.year == 2


def test_course_fuzzy_name(kb: KnowledgeBase) -> None:
    assert "580" in ents("bachelor of commerce accountancy and taxation", kb).course_ids


def test_ambiguous_course_keeps_both(kb: KnowledgeBase) -> None:
    assert set(ents("msc ai and ml", kb).course_ids) == {"621", "955"}


def test_one_year_disambiguates(kb: KnowledgeBase) -> None:
    assert ents("what will i learn in the msc ai and ml one year", kb).course_ids == ["955"]
    assert ents("msc ai and ml two year course", kb).course_ids == ["621"]


@pytest.mark.parametrize(
    "text,dept",
    [
        ("where is the commerce department", "Department of Commerce"),
        ("computer science department", "Department of Computer Science"),
        ("law department", "School of Law"),
        ("psychology courses", "Department of Psychology"),
    ],
)
def test_departments(text: str, dept: str, kb: KnowledgeBase) -> None:
    assert ents(text, kb).department == dept


def test_generic_and_stairs(kb: KnowledgeBase) -> None:
    e = ents("nearest toilet by the stairs", kb)
    assert e.category_request == "washroom" and e.prefer_stairs


@pytest.mark.parametrize(
    "text,cat",
    [
        ("fees for karnataka students", "karnataka"),
        ("other state", "other_states"),
        ("oci", "oci"),
        ("african student", "saarc"),
        ("international student", "foreign"),
    ],
)
def test_fee_categories(text: str, cat: str, kb: KnowledgeBase) -> None:
    assert ents(text, kb).fee_category == cat


def test_date_ref(kb: KnowledgeBase) -> None:
    assert ents("is the library open tomorrow", kb).date_ref == "tomorrow"


def test_degree_abbreviation_expands(kb: KnowledgeBase) -> None:
    assert "580" in ents("tell me about the bcom accountancy and taxation course", kb).course_ids


def test_print_documents_is_xerox(kb: KnowledgeBase) -> None:
    assert ents("where can I print documents", kb).place_ids == ["xerox_shop"]


def test_phd_in_cs(kb: KnowledgeBase) -> None:
    assert ents("tell me about phd in computer science", kb).course_ids == ["47"]
