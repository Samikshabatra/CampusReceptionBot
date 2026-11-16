import pytest

from reception.kb.layout import expand_layout
from reception.kb.loader import KnowledgeBase

EXPECTED_ROOMS = {
    "1": {
        *map(str, [101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 114, 115]),
    },
    "2": {str(n) for n in range(201, 220)},
    "3": {str(n) for n in range(301, 320)},
    "4": {*map(str, range(402, 410)), *map(str, range(411, 416))},
    "5": {str(n) for n in range(502, 516)},
    "6": {*map(str, range(601, 609)), *map(str, range(611, 616))},
    "7": {"711", *map(str, range(713, 720))},
    "8": {"808", "809", "810", "812", "813", "814", "815"},
    "9": {str(n) for n in range(901, 916)},
    "10": {"1000", *map(str, range(1001, 1005)), *map(str, range(1006, 1010))},
}


def test_expand_layout_even_split_and_span() -> None:
    raw = {
        "floor": "8",
        "rows": [
            {
                "box": [14, 0, 86, 10],
                "direction": "horizontal",
                "cells": [{"id": "faculty_staff_room", "span": 4}, "gw", "wd"],
            },
        ],
    }
    cells = dict(expand_layout(raw))
    assert cells["faculty_staff_room"].w == pytest.approx(4 * cells["8_gw_1"].w)
    assert cells["8_wd_1"].x + cells["8_wd_1"].w == pytest.approx(86)


def test_expand_layout_merges_duplicates() -> None:
    raw = {
        "floor": "B",
        "rows": [
            {"box": [0, 0, 10, 60], "direction": "vertical", "cells": ["shop", "shop", "gap"]}
        ],
    }
    cells = dict(expand_layout(raw))
    assert cells["shop"].h == pytest.approx(40)
    assert "gap" not in cells


def test_rooms_per_floor_match_map(kb: KnowledgeBase) -> None:
    for floor, expected in EXPECTED_ROOMS.items():
        got = {p.room_number for p in kb.places.values() if p.floor == floor and p.room_number}
        assert got == expected, floor


def test_absent_rooms(kb: KnowledgeBase) -> None:
    assert all(f"room_{r}" not in kb.places for r in ["806", "805", "811", "109", "1005"])


def test_every_place_has_rect_inside_grid(kb: KnowledgeBase) -> None:
    for p in kb.places.values():
        if p.whole_floor:
            continue
        assert p.rect is not None, p.id
        r = p.rect
        assert 0 <= r.x and r.x + r.w <= 100 and 0 <= r.y and r.y + r.h <= 60, p.id


def test_named_places(kb: KnowledgeBase) -> None:
    assert kb.places["xerox_shop"].floor == "B"
    assert kb.places["library"].floor == "6"
    assert kb.places["mca_lab"].floor == "8"
    assert kb.places["admissions_office"].primary
    assert kb.places["room_110"].group == "admissions"
    assert kb.places["room_1000"].group == "media_studies" and kb.places["room_1000"].primary
    assert "room_c101" not in kb.places
    assert kb.places["office_accounts_exams"].floor == "1"
    assert kb.places["documentation_room"].floor == "1"
    assert kb.places["office_faculty_management"].floor == "1"
    assert kb.places["placement_office_law"].floor == "5"
    assert kb.places["director_of_law"].floor == "5"
    assert "asst_hod_office" not in kb.places
    assert kb.floors["4"].title == "School of Law" and kb.floors["5"].title == "School of Law"
    assert kb.places["gourmet"].name.startswith("Gourmet")


def test_unknown_labels(kb: KnowledgeBase) -> None:
    unknown = {p.id for p in kb.places.values() if p.category == "unknown"}
    assert unknown == {"8_fw_1", "8_ld_1", "2_lt_1", "3_lt_1", "law_box_9"}


def test_department_targets_exist(kb: KnowledgeBase) -> None:
    for target in set(kb.departments.values()) - {"not_in_central_block"}:
        assert target in kb.places or target in kb.groups, target
