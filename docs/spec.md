# Spec — Multimodal AI Reception Kiosk ("CHRIST Central Block Assistant")

| | |
|---|---|
| Date | 2026-11-04 |
| Status | Draft — awaiting approval |
| Source brief | `Downloads/problem 2 - Deepa V. Jose.docx.pdf` |
| Source data | Central Block floor map (image), `CHRIST_Central_Campus_Courses.csv`, `ACADEMIC CALENDAR 2026-2027_*.pdf`, office/library timings and contacts given in chat |

Items marked **[ASSUMPTION]** were not confirmed by the team; each is listed again in §15 so it can be checked.

> **Updates after approval (2026-11-04, from the team):**
> 1. **Start point:** directions are given as if the visitor stands at the **Reception on the Ground floor** (kiosk node `G:kiosk`, in front of the counter). Wherever this spec says the kiosk is on the 8th floor, read Ground-floor Reception.
> 2. **Final floor map:** 1st floor now has *Office of Accounts and Exams*, *Documentation Room*, *Office of Faculty Management* (C101 Media Studies and the 1F washrooms removed); 4th and 5th floors are the **School of Law** (5F: *Placement Office (Law)*, *Director of Law*; Asst. HoD Office removed); 9th floor is general classrooms; its "Dept. of Law" box is drawn but not used — **the team confirmed Law is on the 4th floor**; 10th floor is the **Department of Media Studies** (Room 1000 only); "Gourmet" spelled correctly.
> 3. **Map conflicts kept as assumptions:** 8th floor shows "812" twice (upper box kept as 813); 3rd-floor top row still garbled (316–319 kept).
> 4. **Topics the knowledge does not cover** (placements, salaries, seats, hostel, syllabus, timetable, cut-offs, results, rankings, parking, transport, Wi-Fi, VC/principal) hand over to reception instead of answering something adjacent.


---

## 1. Intent

Reception staff at CHRIST's Central Block answer the same questions all day — *where is room X, when is the library open, what does MCA cost, who do I call about admissions* — and get swamped when several visitors arrive together.

We are building a **kiosk on the 8th floor** (the "Current Location" in the centre lobby of the map, Department of Computer Science) that:

1. Notices a visitor walking up and greets them — no button.
2. Lets them ask by **voice or by typing/tapping**.
3. Answers **out loud and on screen at the same time** — for directions, it shows the floor map with the route and the destination highlighted.
4. **Only states facts it can find in the verified knowledge base.** When it can't, it says so and hands over to a human.
5. Logs every interaction anonymously so staff can see what visitors ask.
6. Comes with **measured numbers** for every AI component (the brief requires nine metrics — §11).

The brief's own example: *"Where is Room 806?" → robot speaks the answer + displays the floor map + highlights Room 806.* The user's own example: *"Where is the xerox shop?" → "The Xerox / Print Shop is in the Basement…" + the route map.*

## 2. Goals, non-goals, anti-goals

**Goals (v1)**
- All 12 capabilities of the brief, end to end, on one laptop-class machine.
- Knowledge base covering the **whole Central Block (Basement–10th)**, richest detail on the 8th floor; every route starts from the kiosk on the 8th floor.
- Knowledge lives in plain editable files; staff can update facts **without retraining or touching any model**.
- An evaluation harness that produces every metric in §11 from committed test sets.

**Non-goals**
- Face recognition or identifying people (brief says not needed; also keeps logs anonymous).
- Robot movement (brief: optional). The kiosk is static.
- Other campuses (Kengeri, Bannerghatta Road, Yeshwanthpur). Calendar items for them are dropped.
- Logging in to university systems, booking appointments, payments, applying for admission.
- Languages other than English in v1 **[ASSUMPTION]**.

**Anti-goals — failure even if everything "works"**
- The kiosk states a room, fee, phone number, date or timing that is **not in the knowledge base**.
- It greets people who are just walking past, or re-greets the same person every few seconds.
- It stores face images, voice recordings or anything that identifies a visitor.
- It reads URLs aloud character by character, or speaks long monologues. Speech is short; detail goes on screen.
- It sends someone to a room that the map doesn't show (e.g. guessing where 805 is).

## 3. Constraints

- **Hardware** **[ASSUMPTION]**: one Windows laptop (or mini-PC), USB webcam, USB microphone, speaker, a monitor (touchscreen preferred; mouse/keyboard acceptable). Must run fully on CPU.
- **Connectivity** **[ASSUMPTION]**: must work **offline**. A cloud LLM may be switched on by config if internet is available.
- **Project conventions** (from `Downloads/CLAUDE.md`): Python 3.12+, `uv`, config in YAML (no hard-coded thresholds), ruff + black + mypy + pytest, seeds set and logged, experiment tracking (MLflow, local) for any trained component and for evaluation runs, fixed train/val/test splits with a documented seed, test sets touched once at the end, `data/` and model weights git-ignored, conventional commits.
- **Privacy**: camera frames processed in memory only; never written to disk. Audio not stored, except eval recordings made with participant consent.
- **Time zone**: Asia/Kolkata. "Open now?" answers use the kiosk's clock.

## 4. Experience

### 4.1 States

```
IDLE (attract screen: "Hi! Ask me anything about Central Block")
  └─ visitor approaches (§6) ─► GREETING (spoken + on screen)
        └─► LISTENING ◄──────────────┐
              ├─ speech / typed / tap │
              ▼                       │
           THINKING ─► ANSWERING ─────┘   (follow-ups keep context)
              └─ uncertain ─► CLARIFY (one question, tap options) ─► LISTENING
              └─ can't verify / asked for a person / urgent ─► HANDOVER
  session ends: visitor gone ≥ 10 s AND no input ≥ 20 s, or "bye/thanks" ─► IDLE (context wiped)
```

All timeouts live in `configs/app.yaml`.

### 4.2 Greeting
Time-aware, short: *"Good morning! I'm the Central Block assistant. Ask me where a room is, about courses and fees, timings, or contacts."* The screen shows the same text plus quick-tap buttons: **Find a place · Courses & fees · Timings · Contacts · Events · Talk to a person**.

### 4.3 Input
- **Voice**: listening opens automatically after the greeting; voice-activity detection decides when the visitor has finished. A mic indicator shows when it is listening. No wake word.
- **Typed**: on-screen keyboard text box, always available.
- **Tap**: quick buttons, clarification options, and suggested follow-ups ("How do I get there?", "Fees for NRI?").

### 4.4 Output — every answer has two parts
- **Speech**: ≤ ~40 words, plain, no URLs, phone numbers read in groups.
- **Screen**: a card matching the answer type — map + route, course card, fee table, timings card, contacts card with QR codes, events list, or handover card. **Every link and phone number is shown as text + QR code.** The source ("From: floor map", "From: Academic Calendar 2026-27", course page link) is shown in small text.

### 4.5 Several visitors at once
One conversation at a time. The detector tracks everyone in view; the first person to approach gets the session. If another person approaches during a session, the screen shows a quiet banner — *"I'll be with you in a moment"* — with no speech interruption. When the session ends, the next waiting person is greeted.

## 5. Architecture

```
 Camera ─► Vision (person detect + track + approach) ──► Session manager
 Mic ────► VAD ─► STT ─────────┐                              │
 Touch/typed (browser) ────────┤                              │
                               ▼                              │
                  Dialogue core (per session context)  ◄──────┘
                  1. normalise text
                  2. resolve follow-ups (it / there / that course)
                  3. intent + entities  (classifier → LLM fallback)
                  4. route to answer engine
                     ├─ Navigation engine   (location registry + nav graph)   deterministic
                     ├─ Timings engine      (rules + calendar)                deterministic
                     ├─ Courses engine      (structured course table)          deterministic
                     ├─ Contacts / Faculty / Events engines                    deterministic
                     └─ Grounded RAG        (retrieve → LLM compose → verify)  generative
                  5. guard (confidence, verification, safety) ─► answer | clarify | handover
                               │
                               ▼
              Response {speech, display card, links, sources, verified}
                 ├─► TTS ─► speaker
                 ├─► Kiosk UI (WebSocket)
                 └─► Analytics log (SQLite)
 Knowledge files (knowledge/*.yaml|json|svg) ─► loaders + validators + search index  (hot-reload)
```

**Key design decision — facts come from code paths, not from the LLM.** Most visitor questions (where, when, how much, whom to call) are answered by deterministic engines reading the knowledge files, filled into fixed templates. The LLM is used only for (a) understanding queries the classifier is unsure about, (b) rewriting follow-up questions into stand-alone ones, and (c) composing answers to open questions ("what is the MCA programme about?") **from retrieved passages only**, followed by a verification check (§8). This keeps hallucination near zero for the high-traffic questions and makes it measurable for the rest.

**Process layout (default; builder may change):** one Python backend (FastAPI) owns camera, microphone, speaker, models and the knowledge base; the kiosk UI is a browser page in full-screen kiosk mode talking over a WebSocket. The admin/analytics pages are served by the same backend behind a PIN.

## 6. Vision — visitor detection

- **Model**: a small person detector (YOLO-n class model, CPU) with multi-object tracking, ~10 fps on 640×480 **[builder may swap for MediaPipe if faster]**.
- **"Approaching", not "present"** — a track triggers a greeting only when, over a window of ~1.5 s:
  - its bounding-box height grows (moving towards the kiosk) **or** it is already large (close), **and**
  - it is roughly centred in frame, **and**
  - it stays (dwell) rather than crossing the frame.
- **Cooldown**: the same track is never greeted twice; a session cannot restart within N seconds after it ends.
- **Privacy**: no face crops, no identity, no frames saved.
- **Second vision capability (stretch)**: room-number / sign recognition — the visitor holds up a slip or phone showing a room number; OCR reads it and the kiosk routes to it.

## 7. Speech

- **STT**: Whisper-family model running locally on CPU (e.g. `small.en`, int8), with a custom vocabulary prompt (room numbers, "CCD", "Gourmet", "MCA", "BCA", "xerox", department names).
- **VAD**: neural VAD to detect start/end of an utterance; max utterance length configurable.
- **TTS**: offline neural TTS (e.g. Piper), with an Indian-English OS voice as fallback. Phone numbers are spoken in digit groups; room numbers digit by digit ("eight zero six") — configurable.
- **Barge-in (stretch)**: speech from the visitor stops TTS playback.

## 8. Understanding and answering

### 8.1 Intents (v1)

| Intent | Example | Engine |
|---|---|---|
| `navigate` | "Where is room 806?", "zerox shop?", "where can I get coffee" | Navigation |
| `facility_hours` | "Is the library open now?", "accounts office timings" | Timings |
| `college_open` | "Is the college open today?" | Timings (answers per facility) |
| `course_info` | "Tell me about MSc AI and ML", "how long is BCA" | Courses / RAG |
| `course_fees` | "MCA fees for NRI", "second year fee BCA" | Courses |
| `course_list` | "What courses does Computer Science offer?", "PG courses in psychology" | Courses |
| `admissions` | "How do I apply?", "admission interview dates" | Contacts + Events |
| `contact` | "Reception number", "admissions email" | Contacts |
| `faculty` | "Where is Prof X?", "where do CS faculty sit" | Faculty |
| `events` | "When is the open day?", "any holidays this month?" | Events |
| `library` | "Library website", "can I borrow books" | Timings + Contacts + RAG |
| `human` | "Can I talk to someone?" | Handover |
| `urgent` | "I feel unwell", "lost my child", "emergency" | Handover (immediate) |
| `greeting` / `thanks_bye` / `repeat` / `smalltalk` | "hi", "thanks", "say that again" | Templates |
| `out_of_scope` | "What's the weather?", "who won the match" | Polite decline |

**Classifier**: sentence embeddings + a light classifier (e.g. logistic regression) trained on a labelled utterance set (§11), seed-fixed, tracked in MLflow. If top-class confidence < τ_intent, the LLM classifies with the intent list as a constrained choice; if still unsure → clarify.

**Entities**: room numbers (3–4 digit numbers and `C101`, spoken forms like "eight zero six" / "eight hundred six" normalised to `806`, then checked against the registry), place names via **fuzzy alias matching** against the location registry (handles "zerox", "photocopy", "canteen", "coffee", "toilet", "restroom", "lift"), course names via fuzzy match + abbreviations (MCA, BCA, MSc AIML, MBA), fee category (Karnataka / other state / NRI / OCI / SAARC-Africa-PIO-ASEAN / foreign), year of study (1–5), department, date expressions ("today", "this Saturday", "next week").

### 8.2 Conversation context
Per session: last N turns plus a **slot memory** (last location, last course, last department, last fee category). "How do I get there?" → last location. "And for NRI?" → last course + new category. "What about its duration?" → last course. Context is wiped when the session ends.

### 8.3 Navigation engine (the user's explicit requirement)
1. Resolve the destination to a **location record** (§9.2). Generic requests ("washroom", "water", "lift") resolve to the **nearest** one — on the 8th floor first.
2. Compute the shortest path on the nav graph from `kiosk_8F` to the destination (lifts preferred over stairs by default; "by stairs" honoured).
3. **Speak** floor + short directions: *"The Xerox and Print Shop is in the Basement. Take the lift right behind me down to B. When you step out, it's along the right-hand wall, next to the Stationery Shop."*
4. **Show** a two-panel map: (a) the **8th floor** with the route from "You are here" to the lift, (b) the **destination floor** with the route from the lift to the destination, destination highlighted and pulsing. Same-floor destinations show one panel. Written step list under the map.
5. Location exists in data but has a known problem (e.g. two Admissions offices) → show both, say which is the main one (§15).
6. **Room not on the map** (e.g. 805, 811, 1005) → controlled reply: *"I couldn't find Room 805 on the Central Block map. Please check with the reception desk."* + handover card. Never guess from numbering.
7. **Department not in Central Block** (15 departments in the course data, e.g. Commerce, Life Sciences) → *"According to my records, the Department of Commerce isn't in Central Block. The reception desk can direct you."* + reception contacts.

Left/right phrasing depends on which way the kiosk faces; that is a config value (`kiosk.facing`) measured on installation. Until set, directions use map-relative landmarks ("past the CCD, towards room 808") **[ASSUMPTION]**.

### 8.4 Timings engine
Rules, in order of precedence (first match wins), evaluated for the requested facility and date:

1. **Public holiday** (calendar) → closed. Applies to offices and the library.
2. **Override working Saturday** (calendar: 17 Oct, 21 Nov, 19 Dec 2026) → treat as normal Mon–Sat day.
3. **Third Saturday** → offices closed; library 9:00–18:00.
4. **Vacation** → library 8:00–17:00; offices normal **[ASSUMPTION]**.
5. **Sunday** → offices closed **[ASSUMPTION]**; library 10:00–18:00.
6. **Mon–Sat** → offices 9:00–17:00, lunch 13:00–14:00; library 8:00–21:00.

Answers say open/closed **now**, next opening time, and lunch break if relevant ("Open now, but closed for lunch from 1 to 2"). "Is the college open today?" answers per facility (offices vs library). Facilities with unconfirmed hours (CCD, Gourmet, Health Centre, Stationery, Xerox) use office hours with `verified: false`, so the kiosk adds *"— please confirm at reception"* **[ASSUMPTION]**. The calendar ends 1 Jun 2027; after that the kiosk says its calendar isn't updated rather than guessing.

### 8.5 Courses engine
- Lookup by fuzzy name / abbreviation / department / level.
- **Fees**: if the category is given, speak that one; otherwise speak Karnataka and Other Indian States for Year 1, and show the full table (all six categories × all years, plus payment deadlines) on screen. Always add "for academic year 2027, as published" and the course page QR.
- Values marked "Not Published" / "Not Applicable" are said as such — never filled in.
- Registration fee: only the 9 rows with a real value are used; otherwise "not listed — please contact Admissions" + contacts.
- Long descriptions are summarised by the RAG path (8.6), never invented.

### 8.6 Grounded RAG (open questions)
- **Corpus**: course descriptions (chunked), location descriptions, facility notes, FAQ entries, calendar events. Each chunk has an ID and source link.
- **Retrieval**: hybrid BM25 + embedding search (small English embedding model), top-k (config). Corpus is small (≈ hundreds of chunks), so an in-memory index is enough.
- **Gate**: if the best score < τ_retrieval → no LLM call, controlled reply + handover.
- **Compose**: LLM gets the question + retrieved chunks + strict instructions: answer only from the chunks, cite chunk IDs, ≤ 40 spoken words, say "NOT_FOUND" if the chunks don't answer it.
- **Verify** (explicit hallucination prevention, required by the brief):
  1. Must cite ≥ 1 retrieved chunk ID; no citation → reject.
  2. Every number, date, room, phone, email and URL in the answer must appear verbatim (after normalisation) in the cited chunks → otherwise reject.
  3. Answer "NOT_FOUND" → controlled reply.
  4. Rejected → controlled reply: *"I could not verify that information. Please contact the reception desk."* + reception contacts.
- **LLM provider**: pluggable. Default local via Ollama (7–8B instruct model) for offline; optional cloud model by config (e.g. `claude-haiku-5-5`). Temperature 0.

### 8.7 Faculty
- "Where is Prof X?" → *"I don't have individual faculty locations. Computer Science faculty sit in the Faculty Staff Room on this floor, and you can look up staff on KnowledgePro."* + KnowledgePro QR (`https://kp.christuniversity.in/KnowledgePro/StudentLogin.do`) + Faculty Staff Room route.
- Department named and mapped (e.g. Law) → offer directions to that department's area.

### 8.8 Human handover
Triggers: low intent confidence twice in a row; retrieval gate fail; verification fail; room/department not found; explicit request; `urgent` intent; repeated "that's wrong / not helpful".
Action: speak the controlled line, show the **handover card** (reception phones, admissions phone/email, general email, all with QR), log the interaction as `handover=true` with reason. `urgent` also shows the Health Centre route (Basement) first.
**Stretch**: push a notification to a reception dashboard page.

## 9. Knowledge base

All under `knowledge/`, committed to git, human-editable, validated by a schema check on load. **Changing a fact = editing a file + pressing "Reload" in the admin page (or restarting).** No model is retrained.

### 9.1 Files
| File | Contents |
|---|---|
| `locations.yaml` | One record per place (§9.2) |
| `floors/<B,G,1..10>.svg` | Clean vector redraw of each floor; every place is an element whose `id` = location id |
| `nav_graph.yaml` | Per-floor corridor waypoints, door nodes, lift/stair nodes, edges with lengths; vertical edges between floors via lifts/stairs |
| `courses.json` | Cleaned course table (§9.3) |
| `timings.yaml` | Facility hour rules (§8.4) |
| `calendar.yaml` | Holidays, override Saturdays, vacations, visitor-relevant Central Campus events (§9.4) |
| `contacts.yaml` | Phones, emails, important links (§9.5) |
| `faq.yaml` | Short Q/A entries staff can add over time |
| `aliases.yaml` | Synonyms → location/course ids ("zerox", "canteen", "photocopy", "AIML") |

`data/raw/` (git-ignored) keeps the original CSV, calendar PDF and map image; `scripts/build_kb.py` regenerates `courses.json` and checks everything.

### 9.2 Location registry — extracted from the floor map

Each record: `id, name, aliases[], floor, category (room|office|department|facility|washroom|water|lift|stairs|seating|entrance), side (map-relative: top|bottom|left|right|centre), near[], svg_id, door_node, verified, notes`.

Map conventions: every floor has two central staircases, each with a lift; water dispenser (W.D) is in the same position (top-right) on every floor. The kiosk is at the **8th-floor centre lobby**.

| Floor | Places (as on the map) |
|---|---|
| **B — Services & Facilities** | Health Centre; Lost & Found; Gents Washroom; Ladies Washroom; Gourmet (cafeteria; map spells "Gourment"); Stationery Shop; Xerox / Print Shop; 2 staircases + lifts |
| **G — Administrative Offices** | Office of Admissions; Office of Processing & Information Management; Office of Procurement; Conference Room; Accounts Office; Faculty Management Office; Council Room; Reception; Entrance; 2 staircases + lifts |
| **1 — Academic & Student Offices** | Rooms 101–105, 107, 108, 111–115; 106 Research & Development Cell; 110 Office of Admissions; C101 Department of Media Studies; G.W; L.W; W.D |
| **2 — School of Business and Management (MBA)** | Rooms 201–219; Faculty Rooms; L.T; L.S.W; G.W ×2; L.W; W.D; lockers ×2; extra staircase (left, between 203 and 204) |
| **3 — School of Business and Management (MBA)** | Rooms 301–315; top row read as 316–319 **[ASSUMPTION — map text garbled]**; Faculty Rooms; L.T; L.S.W; G.S.W; G.W ×2; L.W; W.D; lockers ×2; extra staircase (left) |
| **4 — Classrooms & Faculty Cabins** | Rooms 402–409, 411–415; Faculty Cabin; L.W; W.D; seating |
| **5 — Classrooms & Faculty Cabins** | Rooms 502–515; F. Cabin (centre); Asst. HoD Office; Faculty Cabin; L.W; W.D |
| **6 — Library, Social Work** | Rooms 601–608, 611–615; **Library**; Department of Social Work; L.W; W.D; seating |
| **7 — Psychological Sciences** | Rooms 711, 713–719; Department of Psychological Sciences; Faculty Cabin; Washroom; G.W; L.W; W.D |
| **8 — Department of Computer Science (kiosk floor)** | Rooms 808, 809, 810, 812, 813, 814, 815; **MCA Lab**; **Faculty Staff Room** (= "Faculty Lounge" in the map key); **CCD** (café); G.W ×2; L.W ×2; W.D; seating ×4; F.W and L.D (meaning unknown — excluded); "You are here" in centre lobby |
| **9 — Department of Law** | Rooms 901–915; Department of Law; G.W; L.W; W.D |
| **10 — Media Studies** | 1000 Department of Media Studies; Rooms 1001–1004, 1006–1009; Experiential Learning Media Lab; Sky View Studio; Green View Studio; Washroom; W.D; seating |

**Known gaps (handled by §8.3 step 6):** no rooms 801–807, 811, 109, 401, 410, 501, 609, 610, 701–710, 712, 1005 on the map. Labels **L.D, F.W (8F)** and **L.T (2F, 3F)** are excluded from navigation until their meaning is confirmed.

### 9.3 Course data cleaning (`scripts/build_kb.py`)
- Keep: Programme ID, name, level, duration, semesters, description, department, school, academic year, registration fee, all fee columns, payment deadlines, **Course Information URL**.
- **Drop**: `Fee Structure URL` (wrong in 150/153 rows) — per user decision, only important URLs are kept.
- Normalise duration ("1 Yrs"/"1 Years" → `1 year`), semesters, fee strings → `{amount, currency}` or `null` + status (`not_applicable`, `not_published`, `modular: …`).
- Registration fee: `&nbsp;` / `of` → `null`.
- Fix encoding (`Master�s` → `Master's`).
- Row 486 has no name → `Master of Science (Forensic Science)` inferred from its description, `verified: false` **[ASSUMPTION]**.
- Self-repeating descriptions (5 rows) → description treated as missing.
- PhD "1 Years" → shown exactly as published ("listed duration: 1 year") **[ASSUMPTION — likely coursework year]**.
- Rows "Not Published" (946, 920) kept, answered as "details not yet published".
- 3 rows with Year-2 deadline "March 15, 2027" kept as published but flagged in the build report.
- Each course gets `location_hint` only when its department is on the map (Computer Science → 8F, Psychology → 7F, Social Work → 6F, Law → 9F, Media Studies → 1F C101 / 10F 1000, Business & Management → 2F–3F); others `not_in_central_block`.

### 9.4 Calendar (AY 2026–27, Central Campus / all-campus only)
- **Holidays (offices + library closed)**: 2026 — 26 Jun, 15 Aug, 26 Aug, 14 Sep, 2 Oct, 10 Oct, 20 Oct, 21 Oct, 26 Oct, 1 Nov, 8 Nov, 10 Nov, 27 Nov, 28 Nov (compensatory); 2027 — 14 Jan, 26 Jan, 6 Mar, 10 Mar, 26 Mar, 8 Apr, 14 Apr, 19 Apr, 1 May, 9 May, 17 May. Plus **25 Dec 2026 (Christmas)** — not listed in the calendar because it falls inside the vacation, added as a holiday **[ASSUMPTION]**. Note in file: holidays may change by Government of Karnataka notification.
- **Third Saturday working days**: 17 Oct, 21 Nov, 19 Dec 2026.
- **Vacations (library vacation hours)** **[ASSUMPTION]**: Christmas 23 Dec 2026 – 3 Jan 2027; Summer 17 Apr – 31 May 2027. (Semester break 18–26 Oct 2026 already past.)
- **Visitor-relevant events**: Daksh & Open Day 21–22 Nov 2026; Admission Interviews 11–13 Dec 2026, 9–14 Apr 2027, 13–15 May 2027; Convocation (Central) 27–29 May 2027; Blossoms inauguration 12 Nov; Annual Athletic Meet 4–5 Dec; Magnificat 5–6 Dec; Christmas Holy Mass 9 Dec; Founder's Day 3 Jan; In-Bloom & Blossoms / Theatre Festival / National Quiz 21–23 Jan; CHRI-SPO Fest 1–6 Feb; Sound Curry 19 Feb; Nritta 27–28 Feb; Open Forum 1 Mar; Gratitude Day 2 Mar; Investiture 3 Mar; exam periods 1–17 Oct 2026 and 9–24 Mar 2027.
- **Excluded**: other-campus events, internal marks-submission deadlines, instruction-day markers.
- Valid until **1 Jun 2027**.

### 9.5 Contacts and links (shown with QR)
- General & Customer Support: +91 80 4012 9100, +91 80 4012 9600
- Admissions Office: +91 92430 80800, +91 80 4012 9400
- General email: mail@christuniversity.in
- Admissions email: admissions@christuniversity.in
- Library website: https://library.christuniversity.in/christ_library/index.php
- KnowledgePro (faculty/staff info): https://kp.christuniversity.in/KnowledgePro/StudentLogin.do
- Per-course: Course Information URL from the CSV.

## 10. Analytics

- **Store**: SQLite, one row per turn + one per session.
- **Turn fields**: random session id, timestamp, input mode (voice/typed/tap), query text (phone numbers and emails masked), STT confidence, intent, intent confidence, entities, engine used, retrieved chunk ids, answer type, `verified`, `handover` + reason, latency per stage (VAD end → STT → NLU → engine/RAG → TTS start), total latency.
- **Session fields**: start, end, duration, turns, ended by (timeout/bye/handover), started by (vision/touch).
- **Never stored**: images, audio, face data, names of visitors.
- **Dashboard** (`/admin`, PIN): most common queries/intents, failed queries (clarify/handover/not-found), average + p95 response time, average interaction duration, most-requested locations, queries needing human intervention, usage by hour/day. CSV export.
- **Admin**: "Reload knowledge base" button showing validation results.

## 11. Evaluation (brief's nine metrics)

Every run logs config, git commit and seed to MLflow; results table goes in the README.

| Measure | Metric | Dataset (built by team, committed under `eval/datasets/`; audio/video git-ignored) | Target |
|---|---|---|---|
| Speech recognition | WER | ≥ 150 recorded utterances, ≥ 10 speakers, quiet + lobby noise, real kiosk questions; consent form | WER ≤ 15% |
| Intent recognition | Accuracy, macro-F1 | ≥ 600 labelled utterances (paraphrases, typos, ASR-style errors), stratified 70/15/15 split, fixed seed | macro-F1 ≥ 0.90 |
| Information retrieval | Precision@k, Recall@k | ≥ 150 queries with gold chunk ids | Recall@5 ≥ 0.90 |
| Answer generation | Correctness, relevance | ≥ 150 questions with gold answers; key-fact match + 2 human raters on a 3-point scale | ≥ 90% correct |
| Hallucination | Error rate | ≥ 100 unanswerable/adversarial items (fake rooms like 820, fake courses, made-up fee categories, staff names, off-campus questions) + the answerable set | ≤ 2% unsupported claims; refusal recall ≥ 0.95 |
| Visitor detection | Precision, recall (event level) | ≥ 60 labelled clips: approach, walk-past, standing nearby, groups, empty lobby | P ≥ 0.90, R ≥ 0.90; false greets reported |
| Response time | Average + p95 latency | Logged on all eval runs | Structured answers: avg ≤ 3 s voice-to-voice, ≤ 1.5 s typed; RAG ≤ 6 s |
| Task completion | Success % | 20 scripted tasks (find room, check library hours, MCA NRI fee, admissions contact, ...) × ≥ 10 participants | ≥ 85% |
| User experience | User score | SUS questionnaire + 1–5 satisfaction, same participants | SUS ≥ 70 |

Also reported: confusion matrix for intents, example successes and failures (including failure cases), end-to-end intent accuracy on STT output vs typed input.

## 12. Repository layout

```
reception-robot/
  configs/          app.yaml (thresholds, timeouts, models, kiosk.facing), intent_train.yaml, eval.yaml
  knowledge/        source of truth (§9) — committed
  data/raw/         original CSV / PDF / map image — git-ignored
  src/reception/
    kb/             loaders, schema validation, search index, hot-reload
    nlu/            normalise, intent classifier, entities, context
    engines/        navigation, timings, courses, contacts, faculty, events
    rag/            retrieve, compose, verify
    dialogue/       session manager, state machine, guard, handover
    speech/         vad, stt, tts
    vision/         detector, tracker, approach logic
    analytics/      logging, queries for dashboard
    app/            FastAPI server, WebSocket, admin routes
  web/              kiosk UI (HTML/JS/SVG), admin dashboard
  scripts/          build_kb.py, train_intent.py, run_kiosk.py, eval_*.py
  eval/datasets/    labelled text sets (audio/video in data/, git-ignored)
  tests/            pytest, mirrors src/
  docs/             this spec, plan, evaluation report
```

## 13. Build order (each milestone is demoable)

1. **Knowledge base** — `build_kb.py`, all `knowledge/` files, 12 floor SVGs + nav graph, validators. *Done when*: every location id has an SVG element and a reachable graph node; course build report shows the fixes in §9.3.
2. **Text assistant (CLI)** — NLU, all engines, RAG + verifier, guard, handover. *Done when*: typed questions return correct structured responses; hallucination set refuses.
3. **Kiosk UI** — answer cards, two-panel route map with highlight, QR codes, quick buttons, typed input. *Done when*: "Where is the xerox shop?" shows 8F → lift → B route with the shop highlighted.
4. **Voice** — VAD, STT, TTS wired into the loop.
5. **Vision** — approach detection → greeting → session lifecycle, multi-visitor banner.
6. **Analytics + admin** — logging, dashboard, KB reload.
7. **Evaluation** — datasets, harness, MLflow, README results table, report.
8. **Stretch** — sign/room-number OCR, barge-in, reception notification, more languages.

## 14. Left to the builder
Exact libraries and model sizes within the stated families; UI visual design; SVG drawing style; corridor waypoint placement; threshold values (tuned on validation data, stored in config); prompt wording; dashboard chart choices.

## 15. Assumptions and open questions (please confirm)

**Most important**
1. **Rooms 801–807 and 811 are not on the map** — and the brief's own demo question is "Where is Room 806?". If those rooms exist, we need their positions; otherwise the kiosk will (correctly) say it can't find 806.
2. Hardware: laptop + USB webcam + mic + speaker + monitor; runs offline on CPU.
3. English only.
4. Kiosk facing direction will be measured at install; until then directions use landmarks.

**Data**
5. Two Admissions offices (Ground floor and Room 110) — both shown; Ground floor treated as main.
6. Two Media Studies locations (C101, 1000) — both shown.
7. 3rd-floor top row read as 316–319.
8. L.D, F.W (8F) and L.T (2F/3F) excluded until meaning confirmed.
9. CCD, Gourmet, Health Centre, Stationery, Xerox hours = office hours, flagged unverified.
10. Offices closed on Sundays; open on normal working days during vacations.
11. Library "vacation" = Christmas 23 Dec–3 Jan and Summer 17 Apr–31 May.
12. Row 486 = MSc Forensic Science (unverified); PhD duration shown as published.
13. 15 departments in the course data are treated as "not in Central Block".
14. 25 Dec 2026 treated as a holiday (not in the calendar's list). Vacation hours for the library apply every non-holiday day in the vacation range, Sundays included.
