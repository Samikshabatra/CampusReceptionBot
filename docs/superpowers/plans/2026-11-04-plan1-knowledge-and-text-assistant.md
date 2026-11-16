# Plan 1 — Knowledge Base + Text Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A typed-text CHRIST Central Block assistant: verified knowledge files + deterministic answer engines + intent/entity understanding + grounded RAG with hallucination checks + human handover, usable from a CLI and fully tested.

**Architecture:** Knowledge lives in `knowledge/` as YAML/JSON (courses cleaned from the CSV by a build script; floor layouts as rows of cells that expand into rectangles on a 100×60 grid per floor). Deterministic engines (navigation over a networkx graph, timings rules, courses, contacts, faculty, events) answer most intents through fixed templates; an embedding + logistic-regression classifier picks the intent, with an LLM fallback; open questions go through hybrid retrieval → LLM compose → verifier. Every turn returns one `Response` object (speech + display card + links + sources), which later plans render in the kiosk UI and speak aloud.

**Tech Stack:** Python 3.12 (via `uv`), pydantic v2, PyYAML, rapidfuzz, networkx, fastembed (`BAAI/bge-small-en-v1.5`, ONNX — no torch), scikit-learn, rank-bm25, httpx (Ollama), mlflow, tzdata; pytest, ruff, black, mypy.

**Spec:** `docs/spec.md` (approved 2026-11-04). Read §8 and §9 before starting any task.

## Roadmap (this plan is 1 of 5)

| Plan | Delivers | Spec milestones |
|---|---|---|
| **1 (this)** | Knowledge base + text assistant + CLI | §13 items 1–2 |
| 2 | FastAPI server, kiosk web UI, generated floor SVGs, two-panel route maps, QR codes | §13 item 3 |
| 3 | Voice (VAD/STT/TTS) + vision (approach detection) + session lifecycle, multi-visitor banner | §13 items 4–5 |
| 4 | Analytics logging, admin dashboard, KB hot-reload | §13 item 6 |
| 5 | Evaluation datasets, harness, MLflow runs, README results table | §13 item 7 |

## Deviations from the spec's file list (§9.1), decided here

- `nav_graph.yaml` is replaced by `floor_template.yaml` + a graph **generated** from the floor layouts, so map and routes can never disagree.
- `floors/*.svg` are **generated** from `floors/*.yaml` in Plan 2 (same ids), instead of hand-drawn.
- `aliases.yaml` is split: place aliases live in `places.yaml`, course abbreviations in `course_aliases.yaml`.
- Card `legs` in responses are plain dicts (`{"floor", "points", "node_ids"}`) so they serialise straight to the UI.

## Global Constraints

- Python **3.12+**, managed by `uv` (`uv sync`, `uv run …`); never `pip install` globally.
- Every threshold, timeout, path and model name lives in `configs/app.yaml`; no magic numbers in code.
- Type hints on every function; Google-style docstrings on public functions; ruff + black + mypy clean.
- Seeds set and logged (`reception.utils.seed.set_seed`) for anything trained; training runs logged to MLflow (`mlruns/`, git-ignored) with config + git commit hash.
- `data/`, `mlruns/`, `.env`, model caches are git-ignored. `knowledge/` is committed.
- Time zone `Asia/Kolkata` for every "now".
- **No git commits or remote actions without the user's explicit yes** (user rule). Each task ends with a *checkpoint* (tests + lint green). If the user approves commits: conventional commits (`feat:`, `fix:`, `test:` …), **no** `Co-Authored-By: Claude` / "Generated with Claude Code" trailers.
- Fixed copy (use verbatim; defined once in `src/reception/copy.py`):
  - `HANDOVER_LINE = "I could not verify that information. Please contact the reception desk."`
  - `ROOM_NOT_FOUND = "I couldn't find Room {room} on the Central Block map. Please check with the reception desk."`
  - `NOT_IN_BLOCK = "According to my records, the {department} isn't in Central Block. The reception desk can direct you."`
  - `UNVERIFIED_SUFFIX = " Please confirm at reception."`
  - `FACULTY_LINE = "I don't have individual faculty locations. Computer Science faculty sit in the Faculty Staff Room on this floor, and you can look up staff on KnowledgePro."`
  - `CALENDAR_EXPIRED = "My calendar isn't updated beyond June 1, 2027. Please check with the reception desk."`
  - `OUT_OF_SCOPE = "Sorry, I can only help with Central Block, courses, timings and contacts."`
  - `REPROMPT = "Sorry, I didn't catch that. You can ask me where a room is, about courses, timings or contacts."`
  - `CLARIFY = "Sorry, I'm not sure what you need. Did you mean one of these?"`
- Speech strings ≤ 40 words (assert in router tests); no URLs inside speech.

## Review Focus

1. **Misspelled / ASR-garbled place names** ("were is the zerox", "libary timing") must still resolve — test in Task 6.
2. **One name, several places** ("admissions office", "media studies") must show all matches with the primary first, not silently pick one — test in Task 4.
3. **Empty, whitespace-only or 2,000-character input** must return `REPROMPT`, never raise — test in Task 9.
4. **Boundary minutes**: exactly 17:00 is closed, 13:00 is lunch, 08:59 library closed — test in Task 3.
5. **Ambiguous course name** ("MSc AI and ML" matches the 1-year and 2-year programmes) must ask a clarify question listing both, not quote one fee — test in Task 9.

---

## File structure (locked)

```
reception-robot/
  pyproject.toml  .gitignore  .python-version  README.md
  configs/app.yaml
  data/raw/                          central_block_map.webp, CHRIST_Central_Campus_Courses.csv, academic_calendar_2026_27.pdf  (git-ignored)
  knowledge/
    courses.json                     generated by scripts/build_kb.py
    course_aliases.yaml              abbreviations → programme ids
    places.yaml                      named places: id → name, aliases, category, primary/group, hours_group, department
    floors/{B,G,1,...,10}.yaml       layout rows of cells per floor
    floor_template.yaml              grid size, corridor ring nodes, lift/stair nodes, kiosk node
    hours.yaml                       hours groups (offices, library, services)
    calendar.yaml                    holidays, working Saturdays, vacations, events, validity
    contacts.yaml                    phones, emails, links
    departments.yaml                 department → location ids or not_in_central_block
    faq.yaml                         short Q/A entries
  src/reception/
    config.py  copy.py  types.py  speech_format.py
    utils/seed.py
    kb/models.py  kb/courses_build.py  kb/layout.py  kb/loader.py
    engines/timings.py  engines/navigation.py  engines/courses.py  engines/info.py   (contacts, faculty, events)
    nlu/normalise.py  nlu/entities.py  nlu/intent.py  nlu/context.py
    llm/base.py  llm/ollama.py
    rag/index.py  rag/verify.py  rag/answer.py
    dialogue/handover.py  dialogue/router.py
  scripts/build_kb.py  scripts/train_intent.py  scripts/chat.py
  eval/datasets/intents.csv
  tests/  (mirrors src/reception/)
```

---

### Task 0: Project scaffold, config, shared types

**Files:**
- Create: `pyproject.toml`, `.python-version`, `.gitignore`, `README.md`, `configs/app.yaml`, `src/reception/__init__.py`, `src/reception/config.py`, `src/reception/copy.py`, `src/reception/types.py`, `src/reception/utils/seed.py`
- Copy into `data/raw/`: the map image (`C:\Users\SAMIKS~1\AppData\Local\Temp\claude\98ef7ea6f3bca3e0\a3b771f4-d474-4173-a5a7-c37f2c6701ae\images\1.webp` → `central_block_map.webp`; if that temp file is gone, ask the user for the map image), `Downloads/CHRIST_Central_Campus_Courses.csv`, `Downloads/ACADEMIC CALENDAR 2026-2027_20261022032320.pdf` → `academic_calendar_2026_27.pdf`
- Test: `tests/test_config.py`, `tests/test_types.py`

**Interfaces — Produces:**
- `AppConfig` (pydantic) with fields: `timezone: str = "Asia/Kolkata"`, `knowledge_dir: Path`, `kiosk_node: str = "8:kiosk"`, `route_preference: Literal["lift","stairs"] = "lift"`, `lift_cost_per_floor: float = 6.0`, `stairs_cost_per_floor: float = 12.0`, `intent_threshold: float = 0.55`, `fuzzy_threshold: int = 80`, `retrieval_threshold: float = 0.45`, `top_k: int = 5`, `max_speech_words: int = 40`, `max_input_chars: int = 500`, `llm: LLMConfig(provider: Literal["ollama","fake"]="ollama", model: str="qwen2.5:7b-instruct", base_url: str="http://localhost:11434", timeout_s: float=30.0)`, `embedding_model: str = "BAAI/bge-small-en-v1.5"`, `intent_model_path: Path = Path("models/intent.joblib")`, `seed: int = 42`
- `load_config(path: Path) -> AppConfig`
- `types.py`:
  - `IntentName = Literal["navigate","facility_hours","college_open","course_info","course_fees","course_list","admissions","contact","faculty","events","library","human","urgent","greeting","thanks_bye","repeat","smalltalk","out_of_scope"]`
  - `Link(label: str, url: str)` — url is `https://…`, `tel:+91…` or `mailto:…`
  - `CardKind = Literal["map","course","fees","course_list","timings","contacts","events","text","handover","clarify"]`
  - `Card(kind: CardKind, data: dict[str, Any])`
  - `Response(speech: str, card: Card, links: list[Link] = [], sources: list[str] = [], verified: bool = True, intent: IntentName, confidence: float, handover_reason: str | None = None, suggestions: list[str] = [])`
- `set_seed(seed: int) -> None` (random, numpy)

- [ ] **Step 1:** `uv init --package --name reception --python 3.12` in `Downloads/reception-robot` (the folder already holds `docs/`); add runtime deps `pydantic pyyaml rapidfuzz networkx fastembed scikit-learn rank-bm25 httpx mlflow tzdata joblib numpy` and dev deps `pytest ruff black mypy types-PyYAML`. Run `uv sync`. Expected: `.venv` created, `uv run python --version` prints 3.12.x.
- [ ] **Step 2:** `.gitignore` contains `data/`, `models/`, `mlruns/`, `.env`, `__pycache__/`, `.venv/`, `*.joblib`. Configure ruff/black line length 100, mypy `disallow_untyped_defs = true`, pytest `testpaths = ["tests"]`.
- [ ] **Step 3: Failing tests**

```python
# tests/test_config.py
def test_load_config_reads_yaml(tmp_path):
    p = tmp_path / "app.yaml"
    p.write_text("knowledge_dir: knowledge\nintent_threshold: 0.7\n")
    cfg = load_config(p)
    assert cfg.intent_threshold == 0.7
    assert cfg.timezone == "Asia/Kolkata"
    assert cfg.kiosk_node == "8:kiosk"

def test_repo_config_loads():
    assert load_config(Path("configs/app.yaml")).llm.provider in ("ollama", "fake")

# tests/test_types.py
def test_response_defaults():
    r = Response(speech="hi", card=Card(kind="text", data={}), intent="greeting", confidence=1.0)
    assert r.links == [] and r.verified is True and r.handover_reason is None
```

- [ ] **Step 4:** Run `uv run pytest -q` → FAIL (imports missing). Implement `config.py`, `types.py`, `copy.py` (strings from Global Constraints), `utils/seed.py`, `configs/app.yaml` (all fields above, explicit values). Run → PASS.
- [ ] **Step 5: Checkpoint:** `uv run pytest -q && uv run ruff check . && uv run black --check . && uv run mypy src` all green.

---

### Task 1: Course data cleaning → `knowledge/courses.json`

**Files:**
- Create: `src/reception/kb/models.py` (course part), `src/reception/kb/courses_build.py`, `scripts/build_kb.py`, `knowledge/course_aliases.yaml`, `knowledge/departments.yaml`
- Test: `tests/kb/test_courses_build.py`

**Interfaces — Produces:**
- `FeeCategory = Literal["karnataka","other_states","nri","oci","saarc","foreign"]` (CSV columns "Karnataka", "Other Indian States", "NRI", "OCI", "SAARC/Africa/PIO/ASEAN", "Other Foreign Nationals")
- `FeeValue(amount: int | None, currency: Literal["INR","USD","EUR"] | None, status: Literal["published","not_applicable","not_published","other"], raw: str)`
- `Course(id: str, name: str, level: Literal["UG","PG","PhD","Certificate / Executive"], duration: str | None, semesters: str | None, description: str | None, department: str, school: str, academic_year: str, registration_fee: str | None, fees: dict[int, dict[FeeCategory, FeeValue]], deadlines: dict[int, str], url: str, verified: bool, location_hint: str | None, notes: list[str])`
- `parse_fee(raw: str) -> FeeValue`
- `normalise_duration(raw: str) -> str | None` — `"1 Yrs"`/`"1 Years"` → `"1 year"`, `"4 Yrs"` → `"4 years"`, `"3 Years / 4 Years (Honours)"` kept as `"3 years / 4 years (Honours)"`, `"Not Published"` → `None`
- `clean_courses(csv_path: Path, departments: dict[str, str]) -> tuple[list[Course], list[str]]` — returns courses + a build report (one line per fix applied)
- `knowledge/departments.yaml`: `{department name as in CSV: location id | "not_in_central_block"}`. Mapped: Computer Science → `dept_computer_science` (8F), Psychology → `dept_psychological_sciences` (7F), Social Work → `dept_social_work` (6F), School of Law → `dept_law` (9F), Media Studies → `dept_media_studies` (place group; C101 + 1000), Business and Management → `school_business_management` (2F–3F). All other 15 → `not_in_central_block`.
- `knowledge/course_aliases.yaml`: `{programme id: [aliases]}` — at least: 50 `[mca]`, 576 `[bca]`, 621 `[msc ai ml, msc aiml, msc artificial intelligence]`, 955 `[msc ai ml one year, msc aiml 1 year]`, 54 `[msc cs, msc computer science]`, 47 `[phd computer science]`, 945 `[phd ai]`.

- [ ] **Step 1: Failing tests** (run against the real CSV in `data/raw/`)

```python
def test_parse_fee_variants():
    assert parse_fee("1,31,000 INR") == FeeValue(amount=131000, currency="INR", status="published", raw="1,31,000 INR")
    assert parse_fee("2,375 USD").amount == 2375
    assert parse_fee("2500 EUR").currency == "EUR"
    assert parse_fee("Not Applicable").status == "not_applicable"
    assert parse_fee("Not Published").status == "not_published"
    assert parse_fee("Modular Programme: Rs.7000 per course/paper (Credit-based Interdisciplinary curriculum)").status == "other"

def test_clean_courses_fixes(courses):           # fixture: clean_courses(real csv)
    by_id = {c.id: c for c in courses}
    assert len(courses) == 153
    assert by_id["486"].name == "Master of Science (Forensic Science)" and by_id["486"].verified is False
    assert all("�" not in c.name + (c.description or "") for c in courses)
    assert by_id["553"].registration_fee is None                 # was "&nbsp;"
    assert by_id["50"].fees[1]["karnataka"].amount == 242000
    assert by_id["50"].location_hint == "dept_computer_science"
    assert by_id["633"].description is None                      # self-repeating description
    assert by_id["946"].duration is None                          # Not Published
    assert sum(c.department == "Department of Computer Science" for c in courses) == 9
    assert not any("Fee Structure" in k for k in Course.model_fields)

def test_build_kb_writes_json(tmp_path):  # scripts/build_kb.py main(out_dir) → courses.json round-trips through Course
```

- [ ] **Step 2:** Run → FAIL. Implement. Row 486 name is inferred only for an empty name whose description starts with "M.Sc., Forensic science"; anything else with an empty name → `name = f"Programme {id}"`, `verified=False`. Self-repeating description = description equals name repeated twice (whitespace-normalised). Keep the 3 rows whose Year-2 deadline says "March 15, 2027" as published but add a note and a build-report line.
- [ ] **Step 3:** `uv run python scripts/build_kb.py` writes `knowledge/courses.json` and prints the report. Run tests → PASS.
- [ ] **Step 4: Checkpoint** (tests + lint).

---

### Task 2: Floor layouts, places, loader

**Files:**
- Create: `src/reception/kb/layout.py`, `src/reception/kb/loader.py`, add place/layout models to `kb/models.py`; `knowledge/floor_template.yaml`, `knowledge/places.yaml`, `knowledge/floors/{B,G,1,2,3,4,5,6,7,8,9,10}.yaml`
- Test: `tests/kb/test_layout.py`, `tests/kb/test_loader.py`

**Layout format (decided):** each floor is a 100 (x) × 60 (y) grid, origin top-left, matching the map panel orientation. A floor file is a list of **rows**; a row has a box `[x0, y0, x1, y1]`, a direction (`horizontal` | `vertical`), and **cells** listed in map order (left→right or top→bottom). Cells split the box evenly unless a cell gives `span: n`.

```yaml
# knowledge/floors/8.yaml
floor: "8"
title: Department of Computer Science
rows:
  - box: [0, 0, 14, 60]
    direction: vertical
    cells: [fw, wd, ld, {id: ccd, span: 2}]               # F.W, W.D, L.D, CCD (CCD + coffee-cup cell)
  - box: [14, 0, 86, 10]
    direction: horizontal
    cells: [{id: faculty_staff_room, span: 4}, gw, wd]
  - box: [86, 0, 100, 60]
    direction: vertical
    cells: ["815", "814", lw, "813", "812", mca_lab]
  - box: [14, 50, 86, 60]
    direction: horizontal
    cells: ["808", "809", "810", gw, lw]
core:                                       # drawn, not navigable
  - {kind: staircase, box: [35, 18, 60, 22], lift: lift_top}
  - {kind: staircase, box: [35, 38, 60, 42], lift: lift_bottom}
  - {kind: seating, box: [22, 22, 28, 28]}  # ×4 as on the map
```

**Cell tokens:** a quoted number (`"808"`, `"C101"`, `"1000"`) → room `room_808` named "Room 808"; a token found in `places.yaml` → that place; generic tokens `gw lw gsw lsw wd washroom lockers` → auto ids `{floor}_{token}_{n}` (category washroom/water/lockers, names "Gents washroom", "Ladies washroom", "Gents staff washroom", "Ladies staff washroom", "Water dispenser", "Washroom", "Lockers"); `staircase` → extra stairs node; tokens `ld fw lt` → `unknown` category (drawn, never a route target). The same id appearing in several cells (like `ccd`) merges into one bounding rect.

**Places (`places.yaml`) — one entry per named place:** `id, name, spoken_name (optional; e.g. "Xerox and Print Shop" for "Xerox / Print Shop"), article: bool = true ("The" before it in speech; false for rooms), aliases[], category (office|department|facility|lab|cafe|shop|library|entrance|reception|studio), floor, primary: bool = true, group: str | None, hours_group: "offices"|"library"|"services"|None, department: str | None`. Must include every named place in spec §9.2, with these groups: `admissions` = {`admissions_office` (G, primary), `room_110` (1F, name "Office of Admissions (Room 110)", primary false)}; `media_studies` = {`dept_media_studies_c101` (1F, primary), `dept_media_studies_1000` (10F)}. Aliases must include at least: xerox_shop `[xerox, zerox, photocopy, print shop, printout, printing]`, gourmet `[gourmet, gourment, cafeteria, canteen, food]`, ccd `[ccd, cafe coffee day, coffee, cafe]`, health_centre `[health centre, clinic, first aid, doctor, medical]`, library `[library, books]`, reception `[reception, front desk, help desk]`, mca_lab `[mca lab, computer lab]`, faculty_staff_room `[faculty staff room, faculty lounge, staff room]`.
`hours_group`: library → `library`; health_centre, gourmet, ccd, stationery_shop, xerox_shop, lost_and_found → `services` (unverified); every other office/department/reception place → `offices`; rooms, washrooms, labs → none.

**Template (`floor_template.yaml`):** corridor ring nodes on every floor: `tl(17,13) tc(50,13) tr(83,13) ml(17,30) mr(83,30) bl(17,47) bc(50,47) br(83,47)`, edges around the ring; `lift_top(61,20)`, `lift_bottom(61,40)`, `stairs_top(35,20)`, `stairs_bottom(35,40)` each linked to the nearest ring node; extra 8F node `kiosk(48,30)` linked to `ml`, `mr`, `lift_top`, `lift_bottom`. Node ids are `"{floor}:{name}"`.

**Interfaces — Produces:**
- `Floor = Literal["B","G","1","2","3","4","5","6","7","8","9","10"]`; `FLOOR_ORDER: dict[Floor,int]` (B=-1, G=0, "1"=1 … "10"=10)
- `Rect(x: float, y: float, w: float, h: float)` with `.center -> tuple[float,float]`
- `Place(id, name, spoken_name: str | None, article: bool, aliases: list[str], category: str, floor: Floor, primary: bool, group: str | None, hours_group: str | None, department: str | None, rect: Rect | None)` — `rect` filled by the loader from the layout
- `expand_layout(raw: dict[str, Any]) -> list[tuple[str, Rect]]` (cell id, rect; merges duplicates)
- `KnowledgeBase` dataclass: `places: dict[str, Place]`, `floors: dict[Floor, FloorLayout]`, `template: FloorTemplate`, `courses: dict[str, Course]`, `course_aliases: dict[str, list[str]]`, `departments: dict[str, str]`, `hours: dict[str, HoursGroup]`, `calendar: CalendarData`, `contacts: list[Contact]`, `faq: list[FaqEntry]`
- `load_kb(root: Path) -> KnowledgeBase` — raises `KnowledgeError` with every problem listed (not just the first)

- [ ] **Step 1: Failing tests**

```python
EXPECTED_ROOMS = {
  "1": {*map(str, [101,102,103,104,105,106,107,108,110,111,112,113,114,115]), "C101"},
  "2": {str(n) for n in range(201, 220)},
  "3": {str(n) for n in range(301, 320)},
  "4": {*map(str, range(402, 410)), *map(str, range(411, 416))},
  "5": {str(n) for n in range(502, 516)},
  "6": {*map(str, range(601, 609)), *map(str, range(611, 616))},
  "7": {"711", *map(str, range(713, 720))},
  "8": {"808","809","810","812","813","814","815"},
  "9": {str(n) for n in range(901, 916)},
  "10": {"1000", *map(str, range(1001, 1005)), *map(str, range(1006, 1010))},
}
def test_expand_layout_even_split_and_span(): ...   # 8F faculty_staff_room rect.w == 4 × gw rect.w
def test_rooms_per_floor_match_map(kb):  # set of room numbers per floor == EXPECTED_ROOMS[floor]
def test_absent_rooms(kb): assert all(f"room_{r}" not in kb.places for r in ["806","805","811","109","1005"])
def test_every_place_has_rect_inside_grid(kb): ...  # 0 ≤ x, x+w ≤ 100, 0 ≤ y, y+h ≤ 60
def test_named_places(kb):
    assert kb.places["xerox_shop"].floor == "B" and kb.places["library"].floor == "6"
    assert kb.places["mca_lab"].floor == "8" and kb.places["admissions_office"].primary
    assert kb.places["room_110"].group == "admissions"
def test_unknown_labels(kb): assert {p.id for p in kb.places.values() if p.category == "unknown"} == {"8_fw_1", "8_ld_1", "2_lt_1", "3_lt_1"}
def test_load_kb_reports_all_errors(tmp_path): ...  # two broken files → KnowledgeError message names both
```

- [ ] **Step 2:** Run → FAIL. Implement `layout.py`, `loader.py`.
- [ ] **Step 3:** Transcribe all 12 floors from `data/raw/central_block_map.webp` in the format above (8F is the worked example; the 3rd-floor top row is `lsw, gsw, "319", "318", "317", "316", gw, wd` per spec assumption 7). Fill `places.yaml`. Run tests until PASS.
- [ ] **Step 4: Checkpoint.**

---

### Task 3: Calendar, hours and the timings engine

**Files:**
- Create: `knowledge/hours.yaml`, `knowledge/calendar.yaml`, `src/reception/engines/timings.py`; models in `kb/models.py`
- Test: `tests/engines/test_timings.py`

**Data (exact values from spec §8.4 / §9.4):**
- `hours.yaml` groups: `offices` {verified: true, weekday: 09:00–17:00, lunch: 13:00–14:00, third_saturday: closed, sunday: closed, vacation: weekday}, `library` {verified: true, weekday: 08:00–21:00, third_saturday: 09:00–18:00, sunday: 10:00–18:00, vacation: 08:00–17:00}, `services` {verified: false, same as offices}.
- `calendar.yaml`: `valid_from: 2026-06-01`, `valid_until: 2027-06-01`, the 26 holidays (25 from the calendar + 2026-12-25 marked `assumed: true`), `working_saturdays: [2026-10-17, 2026-11-21, 2026-12-19]`, vacations `christmas 2026-12-23..2027-01-03`, `summer 2027-04-17..2027-05-31`, and the visitor events list from spec §9.4 (name, start, end, place: "Central Campus").

**Interfaces — Produces:**
- `DayHours(open: time | None, close: time | None, lunch: tuple[time,time] | None, reason: Literal["holiday","third_saturday","sunday","vacation","weekday","working_saturday"], holiday_name: str | None)` — `open is None` means closed
- `day_hours(group: HoursGroup, d: date, cal: CalendarData) -> DayHours` — precedence: holiday → working Saturday (as weekday) → third Saturday (weekday()==5 and 15≤day≤21) → vacation → Sunday → weekday
- `Status(is_open: bool, on_lunch: bool, today: DayHours, next_open: datetime | None, verified: bool)`
- `status_at(group: HoursGroup, at: datetime, cal: CalendarData) -> Status` — open interval is `[open, close)`; lunch `[13:00, 14:00)` counts as not open with `on_lunch=True`
- `class CalendarExpired(Exception)` raised when `at.date()` is outside `[valid_from, valid_until)`

- [ ] **Step 1: Failing tests** (`dt("2026-11-04 10:00")` builds an Asia/Kolkata datetime)

```python
def test_weekday_office_open():            assert status_at(OFF, dt("2026-11-04 10:00"), CAL).is_open
def test_lunch():                          s = status_at(OFF, dt("2026-11-04 13:00"), CAL); assert not s.is_open and s.on_lunch
def test_close_boundary():                 assert not status_at(OFF, dt("2026-11-04 17:00"), CAL).is_open
def test_library_before_open():            assert not status_at(LIB, dt("2026-11-04 07:59"), CAL).is_open
def test_holiday_closes_both():
    assert day_hours(OFF, date(2026,11,10), CAL).reason == "holiday"
    assert day_hours(LIB, date(2026,11,8), CAL).open is None            # Sunday holiday
def test_compensatory_and_override_saturdays():
    assert day_hours(OFF, date(2026,11,21), CAL).open == time(9)        # third Sat but working
    assert day_hours(OFF, date(2026,11,28), CAL).reason == "holiday"
def test_third_saturday():
    assert day_hours(OFF, date(2027,1,16), CAL).open is None
    assert (day_hours(LIB, date(2027,1,16), CAL).open, day_hours(LIB, date(2027,1,16), CAL).close) == (time(9), time(18))
def test_vacation_library_sunday():       assert day_hours(LIB, date(2026,12,27), CAL).close == time(17)
def test_christmas_assumed_holiday():     assert day_hours(LIB, date(2026,12,25), CAL).reason == "holiday"
def test_services_unverified():           assert status_at(SRV, dt("2026-11-04 10:00"), CAL).verified is False
def test_next_open_after_close():         assert status_at(OFF, dt("2026-11-04 18:00"), CAL).next_open == dt("2026-11-05 09:00")
def test_calendar_expired():
    with pytest.raises(CalendarExpired): status_at(OFF, dt("2027-06-02 10:00"), CAL)
```

- [ ] **Step 2:** Run → FAIL. Implement. `next_open` searches forward day by day (max 14 days) using `day_hours`.
- [ ] **Step 3:** Run → PASS. **Checkpoint.**

---

### Task 4: Navigation graph, routes, directions

**Files:**
- Create: `src/reception/engines/navigation.py`, `src/reception/speech_format.py` (floor names part)
- Test: `tests/engines/test_navigation.py`

**Interfaces — Consumes:** `KnowledgeBase`, `AppConfig.kiosk_node / lift_cost_per_floor / stairs_cost_per_floor`.
**Produces:**
- `floor_name(f: Floor) -> str` → `"Basement"`, `"Ground floor"`, `"1st floor"`, `"2nd floor"`, `"3rd floor"`, `"4th floor"` … `"10th floor"`
- `floor_phrase(f: Floor) -> str` → `"in the Basement"`, `"on the Ground floor"`, `"on the 8th floor"`
- `place_phrase(p: Place) -> str` → `"The Xerox and Print Shop"` (uses `spoken_name or name`, prefixes "The" when `article`), `"Room 812"`
- `build_graph(kb: KnowledgeBase, cfg: AppConfig) -> nx.Graph` — ring + lift/stair nodes per floor from the template; every place with a rect gets node `"{floor}:{place_id}"` linked to its nearest ring node (Euclidean weights); lifts link vertically between consecutive floors (`lift_top`↔`lift_top`, `lift_bottom`↔`lift_bottom`) with weight `lift_cost_per_floor`; stairs likewise with `stairs_cost_per_floor`; `unknown` places get no node
- `Route(place_id: str, legs: list[RouteLeg])`; `RouteLeg(floor: Floor, points: list[tuple[float,float]], node_ids: list[str])` — one leg per floor actually walked (vertical travel is the gap between legs)
- `plan_route(kb, g, start: str, place_id: str, prefer: Literal["lift","stairs"]) -> Route` — `prefer="stairs"` multiplies lift edge weights by 10 for this call
- `resolve_places(kb, place_ids: list[str]) -> list[Place]` — expands a group to all members, primary first
- `nearest_of_category(kb, g, start: str, category: str) -> Place` (for "washroom", "water", "lift")
- `directions(kb, route: Route) -> list[str]` — written steps; landmark = the nearest other named place on the destination floor
- `navigation_response(kb, g, cfg, place_ids: list[str], prefer) -> Response` — `card.kind="map"`, `card.data = {"targets": [ids], "legs": [...], "steps": [...], "floors": [floors in walking order]}`; speech pattern for other floors: `"{place_phrase} is {floor_phrase}. Take the nearest lift {up|down} to the {floor_name}. It's on the {side} side, near the {landmark}."`; same floor: `"{place_phrase} is on this floor, on the {side} side, near the {landmark}."`; `unknown` places get no graph node where side ∈ {left, right, top, bottom} from the rect centre relative to the grid centre (map-relative, spec §8.3)

- [ ] **Step 1: Failing tests**

```python
def test_floor_names(): assert [floor_name(f) for f in ("B","G","1","2","3","8","10")] == ["Basement","Ground floor","1st floor","2nd floor","3rd floor","8th floor","10th floor"]
def test_route_to_xerox(kb, g, cfg):
    r = plan_route(kb, g, "8:kiosk", "xerox_shop", "lift")
    assert [leg.floor for leg in r.legs] == ["8", "B"]
    assert any("lift" in n for n in r.legs[0].node_ids) and r.legs[-1].node_ids[-1] == "B:xerox_shop"
def test_same_floor_no_lift(kb, g):     r = plan_route(kb, g, "8:kiosk", "mca_lab", "lift"); assert len(r.legs) == 1
def test_stairs_preference(kb, g):      assert any("stairs" in n for n in plan_route(kb, g, "8:kiosk", "library", "stairs").legs[0].node_ids)
def test_nearest_washroom_on_kiosk_floor(kb, g): assert nearest_of_category(kb, g, "8:kiosk", "washroom").floor == "8"
def test_xerox_speech(kb, g, cfg):
    r = navigation_response(kb, g, cfg, ["xerox_shop"], "lift")
    assert r.speech.startswith("The Xerox and Print Shop is in the Basement. Take the nearest lift down to the Basement.")
    assert r.card.kind == "map" and r.card.data["floors"] == ["8", "B"]
def test_unknown_not_in_graph(kb, g): assert "8:8_ld_1" not in g and "2:2_lt_1" not in g
def test_group_shows_all_primary_first(kb, g, cfg):   # Review Focus 2
    r = navigation_response(kb, g, cfg, ["admissions_office"], "lift")
    assert r.card.data["targets"] == ["admissions_office", "room_110"] and "Ground floor" in r.speech
def test_every_place_reachable(kb, g):  # every non-unknown place has a route from 8:kiosk
```

- [ ] **Step 2:** Run → FAIL. Implement. **Step 3:** PASS. **Checkpoint.**

---

### Task 5: Courses, contacts, faculty, events engines + speech formatting

**Files:**
- Create: `src/reception/engines/courses.py`, `src/reception/engines/info.py`, `knowledge/contacts.yaml`, `knowledge/faq.yaml`; extend `speech_format.py`
- Test: `tests/engines/test_courses.py`, `tests/engines/test_info.py`, `tests/test_speech_format.py`

**Data:** `contacts.yaml` = spec §9.5 exactly (ids: `support_1`, `support_2`, `admissions_1`, `admissions_2`, `email_general`, `email_admissions`, `library_site`, `knowledgepro`). `faq.yaml` starts with ≥ 10 entries drawn only from the data already given (e.g. "Where can I get coffee?" → CCD 8F / Gourmet B; "Is there a lost and found?" → Basement).

**Interfaces — Produces:**
- `speak_inr(amount: int) -> str` — Indian grouping: `242000 → "2 lakh 42 thousand rupees"`, `99000 → "99 thousand rupees"`, `1250000 → "12 lakh 50 thousand rupees"`, `5000 → "5 thousand rupees"`
- `speak_usd(amount: int) -> str` → `"2,375 US dollars"`
- `speak_phone(number: str) -> str` → `"+91 80 4012 9100"` → `"plus 9 1, 8 0, 4 0 1 2, 9 1 0 0"`
- `speak_time(t: time) -> str` → `time(10) → "10 am"`, `time(13) → "1 pm"`, `time(8, 30) → "8:30 am"`; `speak_date(d: date) -> str` → `"21 November"`
- `course_fees_response(kb, course_id: str, category: FeeCategory | None, year: int | None) -> Response` — category given → speak that; none → speak Year-1 Karnataka and Other Indian States; card `fees` holds all categories × years + deadlines; speech ends with `"for academic year 2027, as published."`; `not_published`/`not_applicable` spoken as "not published" / "not applicable"; card shows registration fee or "Not listed — please contact Admissions" (+ admissions contact links); link = course URL
- `course_info_response(kb, course_id) -> Response` — level, duration, semesters, department + location hint ("Computer Science is on this floor" / "on the {floor}" / `NOT_IN_BLOCK` wording); description shown on the card, not spoken
- `course_list_response(kb, department: str | None, level: str | None) -> Response`
- `contact_response(kb, topic: Literal["general","admissions","library","all"]) -> Response` — phones spoken with `speak_phone`, links `tel:`/`mailto:`/`https:`
- `faculty_response(kb, department: str | None) -> Response` — speech = `FACULTY_LINE`; link KnowledgePro; card includes the route to `faculty_staff_room`; if a mapped department other than CS is named, add "{department} is on the {floor}."
- `events_response(kb, today: date, query: Literal["upcoming","holidays","admissions","open_day"]) -> Response` — next 3 matching items from `today`
- `hours_response(kb, place_or_group: str, at: datetime) -> Response` — uses Task 3; unverified groups append `UNVERIFIED_SUFFIX`; `CalendarExpired` → `CALENDAR_EXPIRED` handover
- `college_open_response(kb, at: datetime) -> Response` — one sentence each for offices and library

- [ ] **Step 1: Failing tests**

```python
def test_speak_inr(): assert [speak_inr(x) for x in (242000, 99000, 1250000, 5000)] == ["2 lakh 42 thousand rupees","99 thousand rupees","12 lakh 50 thousand rupees","5 thousand rupees"]
def test_mca_fees_default(kb):
    r = course_fees_response(kb, "50", None, None)
    assert "2 lakh 42 thousand rupees" in r.speech and r.card.kind == "fees" and r.links[0].url.startswith("https://christuniversity.in/courses/")
def test_fee_category(kb): assert "NRI" in course_fees_response(kb, "50", "nri", 1).speech
def test_not_published(kb): assert "not published" in course_fees_response(kb, "946", None, None).speech.lower()
def test_course_info_not_in_block(kb): assert "isn't in Central Block" in course_info_response(kb, "580").speech   # BCom (Accountancy and Taxation)
def test_registration_fee_missing(kb): assert "contact Admissions" in course_fees_response(kb, "50", None, None).card.data["registration_fee"]
def test_faculty(kb): r = faculty_response(kb, None); assert r.speech == FACULTY_LINE and r.links[0].url.startswith("https://kp.christuniversity.in")
def test_library_hours_sunday(kb): assert "10 am to 6 pm" in hours_response(kb, "library", dt("2026-11-15 11:00")).speech
def test_services_suffix(kb): assert hours_response(kb, "xerox_shop", dt("2026-11-04 10:00")).speech.endswith(UNVERIFIED_SUFFIX.strip())
def test_open_day_event(kb): assert "21 November" in events_response(kb, date(2026,11,4), "open_day").speech
@pytest.mark.parametrize("make", ALL_RESPONSE_MAKERS)   # list of lambdas kb -> Response, one per response function above
def test_speech_rules(kb, make): s = make(kb).speech; assert "http" not in s and len(s.split()) <= 40
```

- [ ] **Step 2:** Run → FAIL. Implement. **Step 3:** PASS. **Checkpoint.**

---

### Task 6: Normalisation and entity extraction

**Files:**
- Create: `src/reception/nlu/normalise.py`, `src/reception/nlu/entities.py`
- Test: `tests/nlu/test_normalise.py`, `tests/nlu/test_entities.py`

**Interfaces — Produces:**
- `normalise(text: str, max_chars: int) -> str` — lower-case, strip punctuation except digits, collapse whitespace, truncate to `max_chars`; spoken numbers → digits: "eight zero six" / "eight oh six" / "eight hundred six" / "eight hundred and six" → "806", "ten zero four" → "1004"
- `Entities(room: str | None, place_ids: list[str], category_request: str | None, course_ids: list[str], fee_category: FeeCategory | None, year: int | None, department: str | None, date_ref: Literal["today","tomorrow","saturday","sunday","this_week"] | None, prefer_stairs: bool)` — `category_request` is set for generic asks ("washroom", "toilet", "restroom" → `washroom`; "water" → `water`; "lift", "elevator" → `lift`); `prefer_stairs` when the text contains "stairs"/"staircase"
- `extract_entities(text: str, kb: KnowledgeBase, fuzzy_threshold: int) -> Entities` — room via `\b(c?\d{3,4})\b`; places via rapidfuzz `partial_ratio` over names + aliases ≥ threshold (longest/highest wins; ties keep all); courses via aliases first then `token_set_ratio` over names; categories via keywords (`karnataka`, `other state(s)`, `nri`, `oci`, `saarc|africa|pio|asean`, `foreign|international`); year via "first/1st/year 1" … "fifth"; department via fuzzy over `kb.departments` keys

- [ ] **Step 1: Failing tests**

```python
@pytest.mark.parametrize("text,room", [("where is room eight zero six", "806"), ("Room 806?", "806"), ("eight hundred and twelve", "812"), ("c101 please", "c101")])
def test_rooms(text, room, kb): assert extract_entities(normalise(text, 500), kb, 80).room == room
@pytest.mark.parametrize("text", ["where is the zerox shop", "were is zerox", "I need a photocopy", "print shop"])   # Review Focus 1
def test_xerox_aliases(text, kb): assert extract_entities(normalise(text, 500), kb, 80).place_ids == ["xerox_shop"]
def test_libary_typo(kb): assert "library" in extract_entities(normalise("libary timing", 500), kb, 80).place_ids
def test_course_and_category(kb):
    e = extract_entities(normalise("MCA fees for NRI second year", 500), kb, 80)
    assert e.course_ids == ["50"] and e.fee_category == "nri" and e.year == 2
def test_ambiguous_course_keeps_both(kb): assert set(extract_entities(normalise("msc ai and ml", 500), kb, 80).course_ids) == {"621", "955"}
def test_truncation(): assert len(normalise("a" * 2000, 500)) == 500
def test_generic_and_stairs(kb):
    e = extract_entities(normalise("nearest toilet by the stairs", 500), kb, 80)
    assert e.category_request == "washroom" and e.prefer_stairs
```

- [ ] **Step 2:** Run → FAIL. Implement. **Step 3:** PASS. **Checkpoint.**

---

### Task 7: Intent dataset and classifier

**Files:**
- Create: `eval/datasets/intents.csv`, `src/reception/nlu/intent.py`, `scripts/train_intent.py`, `configs/intent_train.yaml`
- Test: `tests/nlu/test_intent.py`

**Dataset (decided):** columns `text,intent,split`; ≥ 30 hand-written utterances per intent for all 18 intents (≥ 540 rows), varied phrasing, typos and ASR-style errors, Indian-English phrasing ("what is the fees of MCA", "where is zerox"); `split` assigned by a stratified 70/15/15 split with seed 42 written into the file once (`scripts/train_intent.py --assign-splits`, refuses to overwrite existing splits). The `test` split is not used in this plan (Plan 5 touches it once).

**Interfaces — Produces:**
- `class IntentClassifier` with `fit(texts: list[str], labels: list[IntentName]) -> None`, `predict(text: str) -> tuple[IntentName, float]`, `save(path: Path) -> None`, `@classmethod load(path: Path, embedding_model: str) -> IntentClassifier` — fastembed embeddings → `LogisticRegression(max_iter=2000, class_weight="balanced")`
- `scripts/train_intent.py --config configs/intent_train.yaml` — trains on `train`, reports accuracy + macro-F1 + confusion matrix on `val`, logs params/metrics/confusion-matrix image/git hash to MLflow experiment `intent`, saves `models/intent.joblib`

- [ ] **Step 1: Failing tests**

- `IntentRow(text: str, intent: IntentName, split: Literal["train","val","test"])`; `load_intents(path: Path) -> list[IntentRow]` (stdlib `csv`)

```python
def test_dataset_shape():
    rows = load_intents(Path("eval/datasets/intents.csv"))
    assert {r.intent for r in rows} == set(get_args(IntentName))
    assert min(Counter(r.intent for r in rows).values()) >= 30
    assert {r.split for r in rows} == {"train", "val", "test"}
def test_val_macro_f1(trained):         # trained on train split
    assert macro_f1(trained, val_rows) >= 0.85
@pytest.mark.parametrize("text,intent", [("where is the library", "navigate"), ("library timings", "facility_hours"),
    ("how much is the MCA fee", "course_fees"), ("is the college open today", "college_open"), ("I want to talk to a person", "human"),
    ("I feel dizzy", "urgent"), ("what's the weather", "out_of_scope")])
def test_key_examples(trained, text, intent): assert trained.predict(text)[0] == intent
def test_save_load_roundtrip(trained, tmp_path): ...
```

- [ ] **Step 2:** Run → FAIL. Write dataset, implement, train. **Step 3:** PASS; record val macro-F1 in the README "Results (validation, provisional)" table. **Checkpoint.**

---

### Task 8: Grounded RAG — index, LLM client, compose, verify

**Files:**
- Create: `src/reception/llm/base.py`, `src/reception/llm/ollama.py`, `src/reception/rag/index.py`, `src/reception/rag/verify.py`, `src/reception/rag/answer.py`
- Test: `tests/rag/test_index.py`, `tests/rag/test_verify.py`, `tests/rag/test_answer.py`, `tests/llm/test_ollama.py`

**Interfaces — Produces:**
- `class LLM(Protocol): def complete(self, system: str, user: str) -> str`
- `FakeLLM(replies: list[str])` in `llm/base.py` — returns replies in order, then `"NOT_FOUND"` once exhausted; records every `(system, user)` pair in `.calls: list[tuple[str, str]]`
- `OllamaLLM(cfg: LLMConfig)` — POST `{base_url}/api/chat`, `stream: false`, `options: {temperature: 0}`; on timeout/connection error raises `LLMUnavailable`
- `Chunk(id: str, text: str, source: str, url: str | None)`; ids: `course:{id}:{n}`, `place:{id}`, `faq:{n}`, `event:{n}`
- `build_chunks(kb) -> list[Chunk]` — course descriptions split at ~600 chars on sentence boundaries, prefixed with the course name
- `HybridIndex.build(chunks, embedding_model) -> HybridIndex`; `search(query: str, k: int) -> list[tuple[Chunk, float]]` — BM25 + cosine, reciprocal-rank fusion (k=60); returned score is the cosine of that chunk (used for the gate)
- `verify(answer: str, cited: list[Chunk]) -> VerifyResult(ok: bool, reasons: list[str])` — rules from spec §8.6: ≥ 1 citation `[chunk-id]`; every number (digits incl. commas), email, URL, phone and room token in the answer appears in the cited chunks' text after normalisation (strip commas/spaces)
- `rag_answer(question: str, index: HybridIndex, llm: LLM, cfg: AppConfig) -> Response` — gate: top score < `retrieval_threshold` → handover `"retrieval_gate"` with **no LLM call**; prompt demands answer only from chunks, cite ids in brackets, ≤ 40 words, or exactly `NOT_FOUND`; `NOT_FOUND` → handover `"not_found"`; verify fail → handover `"verify_failed"`; `LLMUnavailable` → handover `"llm_unavailable"`; success → speech with citation brackets removed, `sources` = cited ids, card `text` with the passage sources

- [ ] **Step 1: Failing tests**

```python
def test_search_finds_mca(index): assert index.search("what is the MCA programme about", 5)[0][0].id.startswith("course:50:")
def test_verify_rejects_unsupported_number(): assert not verify("Fees are 3,00,000 [course:50:0]", [Chunk("course:50:0", "fee 2,42,000", "csv", None)]).ok
def test_verify_rejects_no_citation(): assert not verify("MCA is a 2 year course.", [CH]).ok
def test_verify_accepts_supported(): assert verify("MCA is a 2 year programme [course:50:0].", [Chunk("course:50:0", "MCA ... 2 year ...", "csv", None)]).ok
def test_gate_skips_llm(index, cfg):
    llm = FakeLLM([]); r = rag_answer("who won the cricket match", index, llm, cfg)
    assert r.handover_reason == "retrieval_gate" and llm.calls == []
def test_not_found(index, cfg): assert rag_answer("what is MCA about", index, FakeLLM(["NOT_FOUND"]), cfg).speech.startswith(HANDOVER_LINE)
def test_hallucinated_number_handover(index, cfg):
    r = rag_answer("what is MCA about", index, FakeLLM(["MCA has 999 seats [course:50:0]"]), cfg)
    assert r.handover_reason == "verify_failed"
def test_ollama_unavailable(cfg):  # base_url to a closed port → LLMUnavailable
```

- [ ] **Step 2:** Run → FAIL. Implement. **Step 3:** PASS. **Checkpoint.**

---

### Task 9: Context, handover and the dialogue router

**Files:**
- Create: `src/reception/nlu/context.py`, `src/reception/dialogue/handover.py`, `src/reception/dialogue/router.py`
- Test: `tests/dialogue/test_router.py`, `tests/nlu/test_context.py`

**Interfaces — Consumes:** everything above. **Produces:**
- `SessionContext(turns: list[tuple[str, Response]], last_place_ids: list[str], last_course_ids: list[str], last_category: FeeCategory | None, last_department: str | None, last_intent: IntentName | None, misunderstandings: int)`
- `resolve(text: str, ents: Entities, ctx: SessionContext) -> Entities` — fills empty place/course/category from context when text contains `there|it|its|that|this|same` or starts with `and|what about|how about`
- `handover_response(kb, reason: str, intent: IntentName, confidence: float, speech: str = HANDOVER_LINE) -> Response` — card `handover` with all contacts; `reason == "urgent"` puts the Health Centre route first and speech `"Please contact the reception desk right away. The Health Centre is in the Basement."`
- `class Assistant(kb, cfg, classifier, index, llm, graph)` with `handle(text: str, ctx: SessionContext, now: datetime) -> Response`:
  1. `text.strip() == ""` → `REPROMPT` (intent `repeat`, conf 0)
  2. `normalise` → `extract_entities` → `resolve`
  3. `classifier.predict`; conf < `intent_threshold` → ask the LLM to reply with exactly one intent name from the list or `unknown`; a valid name is used; `unknown`/anything else/`LLMUnavailable` → clarify card (speech `CLARIFY`, options = the six quick buttons from spec §4.2) and `ctx.misunderstandings += 1`; at 2 consecutive → handover `"low_confidence"`. Text matching `that's wrong|not helpful|wrong answer` also counts as a miss.
  4. Elliptical follow-up ("and for NRI?") with no new intent signal → reuse `last_intent`
  5. Dispatch: `navigate` (room given but not in KB → `ROOM_NOT_FOUND` handover; department not in block → `NOT_IN_BLOCK` handover; generic category → `nearest_of_category`), `facility_hours`, `college_open`, `course_info` (≥ 2 course ids → clarify card listing them), `course_fees` (≥ 2 → clarify), `course_list`, `admissions` (admissions contacts + next admission interview dates), `contact`, `faculty`, `events`, `library` (hours + library site link), `human`/`urgent` → handover, `greeting`/`thanks_bye`/`smalltalk` → fixed templates, `repeat` → last response, `out_of_scope` → `OUT_OF_SCOPE`; anything with no deterministic answer → `rag_answer`
  6. Append to `ctx.turns`, update slots, return
- `scripts/chat.py` — REPL: loads config, KB, classifier, index, `OllamaLLM` (or `FakeLLM` with `--offline`), prints speech, card kind, links, sources

- [ ] **Step 1: Failing tests** (`tests/conftest.py`: session-scoped fixtures `kb`, `cfg`, `g`, `index`, and `classifier` — loads `models/intent.joblib`, or trains on the `train` split if absent; `assistant` uses `FakeLLM([])`; `NOW = dt("2026-11-04 10:00")`)

```python
def test_xerox_then_timings(assistant):
    ctx = SessionContext()
    r1 = assistant.handle("Where is the zerox shop?", ctx, NOW)
    assert r1.intent == "navigate" and r1.card.data["floors"] == ["8", "B"]
    r2 = assistant.handle("what are its timings?", ctx, NOW)
    assert r2.intent == "facility_hours" and r2.speech.endswith(UNVERIFIED_SUFFIX.strip())
def test_room_806_not_on_map(assistant): assert assistant.handle("Where is Room 806?", SessionContext(), NOW).speech == ROOM_NOT_FOUND.format(room="806")
def test_room_812(assistant): assert assistant.handle("where is room 812", SessionContext(), NOW).card.data["targets"] == ["room_812"]
def test_commerce_not_in_block(assistant): assert "isn't in Central Block" in assistant.handle("where is the commerce department", SessionContext(), NOW).speech
def test_fees_followup(assistant):
    ctx = SessionContext(); assistant.handle("MCA fees", ctx, NOW)
    assert "NRI" in assistant.handle("and for NRI?", ctx, NOW).speech
def test_ambiguous_course_clarifies(assistant):          # Review Focus 5
    r = assistant.handle("fees for msc ai and ml", SessionContext(), NOW); assert r.card.kind == "clarify" and len(r.card.data["options"]) == 2
def test_urgent(assistant): r = assistant.handle("I feel unwell", SessionContext(), NOW); assert r.handover_reason == "urgent" and "Basement" in r.speech
def test_faculty(assistant): assert assistant.handle("where is professor sharma", SessionContext(), NOW).speech == FACULTY_LINE
def test_out_of_scope(assistant): assert assistant.handle("what's the weather today", SessionContext(), NOW).speech == OUT_OF_SCOPE
@pytest.mark.parametrize("text", ["", "   ", "x" * 2000])     # Review Focus 3
def test_degenerate_input(assistant, text): assert assistant.handle(text, SessionContext(), NOW).speech in (REPROMPT, OUT_OF_SCOPE, HANDOVER_LINE, CLARIFY)
def test_two_misses_handover(assistant):
    ctx = SessionContext(); assistant.handle("blorp fizzle", ctx, NOW)
    assert assistant.handle("wug snorf", ctx, NOW).handover_reason == "low_confidence"
def test_stairs_route(assistant): assert any("stairs" in n for n in assistant.handle("how do I get to the library by stairs", SessionContext(), NOW).card.data["legs"][0]["node_ids"])
def test_college_open_third_saturday(assistant): assert "library" in assistant.handle("is the college open today", SessionContext(), dt("2027-01-16 10:00")).speech.lower()
def test_calendar_expired(assistant): assert assistant.handle("library timings", SessionContext(), dt("2027-06-05 10:00")).speech == CALENDAR_EXPIRED
def test_speech_limits(assistant):  # every response in this module: ≤ 40 words, no "http"
```

- [ ] **Step 2:** Run → FAIL. Implement. **Step 3:** PASS.
- [ ] **Step 4: Manual smoke** — `uv run python scripts/chat.py --offline`, ask the 8 questions: "Where is the xerox shop?", "what are its timings?", "Where is Room 806?", "MCA fees", "and for NRI?", "Is the library open now?", "When is the open day?", "where is professor sharma". Each prints a sensible speech line and card kind. With Ollama running (`ollama pull qwen2.5:7b-instruct`), also ask "What is the MCA programme about?" and confirm a cited, verified answer.
- [ ] **Step 5: Checkpoint** — full suite + ruff + black + mypy green; README updated with setup (`uv sync`, `uv run python scripts/build_kb.py`, `uv run python scripts/train_intent.py --config configs/intent_train.yaml`, `uv run python scripts/chat.py`) and the provisional results table.

---

## Done when

- `uv run pytest` green, lint/type checks clean.
- `scripts/chat.py` answers the brief's example ("Where is Room 806?" → controlled not-on-map reply, since 806 isn't on the map) and the user's example ("Where is the xerox shop?" → Basement + two-floor route data).
- The knowledge base can be changed by editing `knowledge/` files only; rerunning `build_kb.py` (courses) or restarting picks up changes without retraining.
