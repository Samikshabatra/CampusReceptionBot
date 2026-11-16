# Plans 2–5 — Kiosk UI, Voice + Vision, Analytics, Evaluation

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Checkbox steps; TDD per task; checkpoints = `./check.sh` (no commits without the user's yes).

**Spec:** `docs/spec.md`. **Builds on:** Plan 1 (`Assistant.handle(text, ctx, now) -> Response`, `build_assistant()`, `KnowledgeBase`, `Response`/`Card`/`Link`).

**Architecture (decided):** one FastAPI process owns the assistant, the vision logic, STT and analytics. The kiosk page (full-screen browser on the same machine) owns the devices: it captures camera frames (JPEG, ~5 fps) and microphone audio (16 kHz PCM) and sends them over one WebSocket; it renders cards and speaks replies with the OS voice (`speechSynthesis`). The server sends back responses, state changes (idle / greeting / listening / thinking / answering / handover) and banners.

**Tech added:** fastapi, uvicorn[standard], qrcode (SVG output, no Pillow), opencv-python-headless (Haar face detector bundled with OpenCV — no model download), faster-whisper (`base.en`, int8, ~145 MB download on first use, bundled Silero VAD), jiwer (WER).

## Global Constraints (in addition to Plan 1's)
- All thresholds/timeouts in `configs/app.yaml` under `kiosk:`, `vision:`, `speech:`, `analytics:`.
- Never store camera frames or audio (except eval recordings made deliberately under `data/eval/`).
- Analytics masks phone numbers and emails before writing query text.
- Admin pages require `analytics.admin_pin` (config; overridable by env `RECEPTION_ADMIN_PIN`).
- UI works with touch, mouse and keyboard; every link shows text + QR; nothing requires the visitor to press a button to start (vision greets).

## Review Focus
1. Visitor walks past without stopping → **no greeting** (approach logic) — Plan 3 T1 test.
2. Two people approach while a session is active → second sees banner, no interruption — Plan 3 T3 test.
3. WebSocket disconnect mid-answer → server keeps running; reconnect starts a fresh session — Plan 2 T3 test.
4. Knowledge reload with a broken file → old knowledge keeps serving, errors shown to admin — Plan 4 T2 test.
5. Phone numbers / emails typed by visitors never reach the analytics DB — Plan 4 T1 test.

---

## Plan 2 — Server + kiosk UI + generated floor maps

### Task 2.1: Floor SVG renderer — `src/reception/ui/floor_svg.py`
- `render_floor_svg(kb, floor: str, highlight: list[str] = [], route: list[tuple[float,float]] | None = None, show_kiosk: bool = True, scale: float = 10.0) -> str` — viewBox `0 0 1000 600`; one `<g id="place-{id}" class="cell cat-{category}">` per place with a rect + label (room number, or short name; generic tokens get icons-as-text: "G.W", "L.W", "W.D"); staircases + lifts from the template; seating circles when `seating`; highlighted ids get class `hl`; route as `<polyline class="route">`; kiosk marker "You are here" on the kiosk floor; floor title text.
- Tests (`tests/ui/test_floor_svg.py`): output parses as XML; every place id on that floor appears as `place-{id}`; `hl` class on highlighted; polyline points count == route length; kiosk marker only on 8F; unknown cells drawn with class `cat-unknown`.

### Task 2.2: Presenter — `src/reception/ui/present.py`
- `present(kb, response: Response) -> dict` — `response.model_dump()` plus `maps: [{floor, title, svg}]` for `map` cards (one per leg floor + extra target floors, route drawn on each leg; extra targets highlighted) and for `handover` cards with `place_ids` (urgent → Health Centre route via navigation); `qr: [{label, url, svg}]` for every link (qrcode SVG path image).
- `qr_svg(data: str) -> str`.
- Tests: xerox response → 2 maps (8 then B), B svg contains `place-xerox_shop` with `hl`; links produce QR svgs; urgent handover gets a Health Centre map.

### Task 2.3: Server — `src/reception/server/app.py`
- `create_app(assistant_factory: Callable[[], Assistant] = build_assistant) -> FastAPI` with lifespan building the assistant once.
- `GET /` kiosk page, `/static/*`, `GET /api/health` → `{"ok": true, "places": n, "courses": n}`.
- `WS /ws` messages in: `{"type":"ask","text"}`, `{"type":"new_session"}`, `{"type":"option","text"}`; out: `{"type":"response","data": present(...)}`, `{"type":"state","state":...}`. One `KioskSession` (ctx + timestamps) per connection.
- `scripts/run_kiosk.py` (uvicorn, host 127.0.0.1, port from config `kiosk.port` = 8765), `.claude/launch.json` entry `kiosk`.
- Tests with `TestClient` and a fake assistant (FakeLLM, real KB): health; ask over WS returns response with maps; disconnect then reconnect works; malformed message → `{"type":"error"}` and connection stays open.

### Task 2.4: Kiosk UI — `web/kiosk/{index.html, app.css, app.js}`
- Layout (landscape 1920×1080 and laptop 1366×768): header (CHRIST Central Block · clock · status pill), left column conversation + input + quick buttons, right column card area. Attract screen when idle.
- Renders each card kind: map (two panels side by side with step list), fees table, course card, course list, timings (open/closed badge), contacts (QR grid), events list, text with sources, handover (red-accent, contacts + QR), clarify (option buttons that send the option text).
- Speaks `speech` with `speechSynthesis` (prefer an `en-IN` voice); mic/listening indicator placeholder for Plan 3.
- Verified in the browser preview: ask "Where is the xerox shop?" → two maps with highlighted shop; "MCA fees" → fee table; "where is room 806" → handover card.

---

## Plan 3 — Voice + vision + session lifecycle

### Task 3.1: Approach detector — `src/reception/vision/approach.py`
- `Box(x, y, w, h)` normalised 0–1; `Tracker` (IoU matching, track ids, max age); `ApproachDetector(cfg)` with `update(boxes: list[Box], t: float) -> list[VisionEvent]` emitting `visitor_approaching(track_id)`, `visitor_left`, `crowd(n)`; rule: over `vision.window_s` (1.5 s) the track is centred (|cx−0.5| ≤ `vision.center_tolerance`), and either its height grew ≥ `vision.growth_ratio` (1.15) or it is ≥ `vision.near_height` (0.22), and it persisted ≥ `vision.dwell_s`; a track is greeted once; global cooldown `vision.cooldown_s`.
- Tests with synthetic box sequences: approach → 1 event; walk-past (moves across x, small) → 0; stands far → 0; same person lingering → 1 event only; two people → `crowd(2)`.

### Task 3.2: Face detector backend — `src/reception/vision/detector.py`
- `FaceDetector` (OpenCV Haar `haarcascade_frontalface_default.xml`, scaleFactor/minNeighbors from config) with `detect(jpeg: bytes) -> list[Box]`. Tests on a generated image without faces → []; malformed bytes → [] (no crash).

### Task 3.3: Session lifecycle — `src/reception/server/session.py`
- `KioskSession` state machine: IDLE → GREETING (on `visitor_approaching` or first touch) → LISTENING ↔ THINKING → ANSWERING → LISTENING; HANDOVER; ends when absent ≥ `kiosk.absent_timeout_s` (10) AND no input ≥ `kiosk.idle_timeout_s` (20), or thanks/bye → IDLE (context wiped). `busy_banner` when another track approaches during a session.
- Tests with an injected clock.

### Task 3.4: Speech-to-text — `src/reception/speech/stt.py`
- `Transcriber(cfg)` lazy-loads faster-whisper `speech.model` (`base.en`, int8, CPU) with `initial_prompt` vocabulary (room numbers, CCD, Gourmet, MCA, BCA, xerox, department names); `transcribe(pcm16k: np.ndarray) -> Transcript(text, avg_logprob, duration_s)`; `vad_filter=True`.
- Browser: AudioWorklet downsamples to 16 kHz, energy VAD (threshold + `speech.silence_ms` hang time, `speech.max_utterance_s` cap) and sends one utterance (`{"type":"audio","pcm": base64 float32}`) while LISTENING; mic paused while the kiosk is speaking (no self-hearing).
- Tests: silence → empty text; (optional, marked slow) a generated TTS clip if available.

### Task 3.5: Wire it up
- WS messages `frame` (base64 JPEG) → detector → approach events → session; `audio` → STT → `ask`. Status pill + mic indicator + banner in UI. Verified in the browser with the laptop camera and mic.

---

## Plan 4 — Analytics + admin

### Task 4.1: Logger — `src/reception/analytics/store.py`
- SQLite `data/analytics.db`; tables `sessions(id, started_at, ended_at, started_by, ended_by, turns)` and `turns(id, session_id, ts, mode, text_masked, intent, confidence, entities_json, card_kind, sources_json, verified, handover_reason, latency_ms_json, total_ms, stt_logprob)`.
- `mask_pii(text) -> str` (phones → `[phone]`, emails → `[email]`); `AnalyticsStore.log_turn(...)`, `start_session`, `end_session`; `summary(since) -> dict` (top intents, top queries, failed queries = clarify/handover/not-found, avg + p95 latency, avg session duration, top locations, handover queries with reasons, usage by hour); CSV export.
- Tests: masking; summary numbers on a seeded DB.

### Task 4.2: Admin — `/admin` (PIN form → cookie) with dashboard (vanilla JS + inline SVG bar charts), `/api/admin/summary`, `/api/admin/export.csv`, `POST /api/admin/reload` (rebuilds KB/index/graph; on error keeps old assistant and returns the error list).
- Tests: wrong PIN → 401; reload with broken file keeps serving; summary JSON shape.

---

## Plan 5 — Evaluation

Scripts in `scripts/eval_*.py`, each writing `eval/results/<name>.json` and logging to MLflow (`sqlite:///mlflow.db`, experiment `evaluation`, params incl. config + git commit). `scripts/eval_report.py` regenerates the README results table.

| Script | Dataset | Metric |
|---|---|---|
| `eval_intent.py` | `intents.csv` **test split (touched once)** | accuracy, macro-F1, confusion matrix, failures |
| `eval_retrieval.py` | `eval/datasets/retrieval.yaml` (query → gold chunk ids, ≥ 60) | P@1, P@3, Recall@5, MRR |
| `eval_answers.py` | `eval/datasets/qa.yaml` (question → required key facts, ≥ 60, routed through the full Assistant) | correctness (all key facts present), relevance (intent correct), per-category |
| `eval_hallucination.py` | `eval/datasets/unanswerable.yaml` (≥ 40: fake rooms, fake courses, staff names, seats, placements, off-campus) + answerable set | hallucination rate (unsupported claim reaches speech), refusal recall/precision |
| `eval_tasks.py` | `eval/datasets/tasks.yaml` (20 scripted multi-turn tasks) | task completion % |
| `eval_latency.py` | runs the QA set, timing each stage | avg / p95 latency |
| `eval_asr.py` | `data/eval/asr/*.wav` + `transcripts.csv` (team records) | WER (jiwer); skipped with a clear message if no recordings |
| `eval_detection.py` | `data/eval/vision/*.mp4` + `labels.csv` (team records) | event P/R; skipped if no clips; synthetic-sequence sanity run always |
| `eval_ux.py` | `eval/datasets/sus_responses.csv` (from the user study form `docs/user_study.md`) | SUS score |

Tests: each metric function unit-tested on tiny fixtures (WER, P/R, SUS formula, key-fact matcher).
