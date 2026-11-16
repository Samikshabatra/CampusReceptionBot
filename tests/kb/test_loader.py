import shutil
from pathlib import Path

import pytest

from reception.kb.loader import KnowledgeError, load_kb


def test_load_kb_counts(kb) -> None:  # type: ignore[no-untyped-def]
    assert len(kb.courses) == 153
    assert len(kb.floors) == 12
    assert "media_studies" in kb.groups


def test_load_kb_reports_all_errors(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    shutil.copytree("knowledge", root)
    (root / "floors" / "8.yaml").write_text(
        "floor: '8'\nrows: [{box: [0,0,1,1], direction: vertical, cells: [no_such_place]}]\n"
    )
    (root / "hours.yaml").write_text(":::not yaml")
    with pytest.raises(KnowledgeError) as e:
        load_kb(root)
    msg = str(e.value)
    assert "no_such_place" in msg and "hours.yaml" in msg


def test_event_names_with_commas_survive(kb) -> None:  # type: ignore[no-untyped-def]
    names = [e.name for e in kb.calendar.events]
    assert "In-Bloom & Blossoms, Theatre Festival, National Quiz Championship" in names
