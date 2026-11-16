// Central Block kiosk front end: views, answers, speech. Camera + mic live in av.js.
import { t, getLang, setLang, locale, applyStatic } from "/static/i18n.js?v=9";
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const body = document.body;

// ---------------------------------------------------------------- icons (stroke, 24px grid)
const ICONS = {
  chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z"/>',
  navigate: '<path d="M21 3 3 10.5l7.5 2.9L13.5 21 21 3Z"/>',
  cap: '<path d="m2 9 10-5 10 5-10 5L2 9Z"/><path d="M6 11v5c3 2.5 9 2.5 12 0v-5"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
  phone: '<path d="M5 3h4l2 5-2.5 1.5a11 11 0 0 0 6 6L16 13l5 2v4a2 2 0 0 1-2 2A17 17 0 0 1 3 5a2 2 0 0 1 2-2Z"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
  mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
  send: '<path d="M21 3 10 14M21 3l-7 18-4-7-7-4 18-7Z"/>',
  pin: '<path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21Z"/><circle cx="12" cy="9.5" r="2.5"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14a6 6 0 0 1 3.5 6"/>',
  right: '<path d="m9 5 7 7-7 7"/>',
  left: '<path d="m15 5-7 7 7 7"/>',
  building: '<path d="M4 21V5l8-3 8 3v16M9 21v-5h6v5M8 8h1M15 8h1M8 12h1M15 12h1"/>',
  book: '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2V5Z"/><path d="M4 19a2 2 0 0 1 2-2h13"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  flag: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
  lift: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="m9 9 3-3 3 3M9 15l3 3 3-3"/>',
  turn: '<path d="M9 20v-7a4 4 0 0 1 4-4h6M15 5l4 4-4 4"/>',
  hourglass: '<path d="M6 3h12M6 21h12M7 3c0 5 10 5 10 9s-10 4-10 9M17 3c0 5-10 5-10 9s10 4 10 9"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
  link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
  star: '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9L12 3Z"/>',
  trophy: '<path d="M8 4h8v5a4 4 0 0 1-8 0V4ZM8 6H4a4 4 0 0 0 4 4M16 6h4a4 4 0 0 1-4 4M12 13v4M8 21h8M9 21l1-4h4l1 4"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  alert: '<path d="M12 3 2 21h20L12 3Z"/><path d="M12 10v5M12 18v.5"/>',
};
function icon(name) {
  return `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ICONS.info}</svg>`;
}
function hydrateIcons(root = document) {
  for (const i of $$("i[data-icon]", root)) i.outerHTML = icon(i.dataset.icon);
}

// ---------------------------------------------------------------- DOM helpers
function el(tag, attrs = {}, ...children) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k === "html") n.innerHTML = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null && v !== false) n.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    n.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return n;
}
const svgNode = (markup) => { const d = document.createElement("div"); d.innerHTML = markup; return d.firstElementChild; };
const iconNode = (name) => svgNode(icon(name));
async function getJSON(url) { const r = await fetch(url); if (!r.ok) throw new Error(`${url}: ${r.status}`); return r.json(); }

// ---------------------------------------------------------------- state + status
const STATUS = { idle: "ready", listening: "listening", thinking: "thinking", answering: "answering",
  navigating: "navigating", handover: "handover" };
function setState(state) {
  // "Listening" only while the visitor has the microphone switched on.
  if (state === "listening" && body.dataset.mic !== "on") state = "idle";
  body.dataset.state = state;
  const visitor = body.dataset.presence === "yes" && state === "idle";
  $("#status-text").textContent = visitor ? t("visitor_detected") : STATUS[state] ? t(STATUS[state]) : state;
}
function setView(view) {
  if (body.dataset.view === view) return;
  body.dataset.view = view;
  for (const b of $$(".nav-item")) b.classList.toggle("is-active", b.dataset.go === view);
  const v = $(`.view-${view}`);
  v.classList.remove("is-entering"); void v.offsetWidth; v.classList.add("is-entering");
  if (view === "navigate" && !route) showPlaceBrowser();
  if (view === "courses" && !courses.loaded) loadCourses(courses.dept);
  if (view === "events" && !cal.loaded) loadCalendar(cal.year, cal.month);
  if (view === "contacts" && !contactsLoaded) loadContacts();
}

// ---------------------------------------------------------------- socket
let ws;
const handlers = new Set();
export function onMessage(fn) { handlers.add(fn); }
export function sendRaw(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ t: performance.now() / 1000, ...obj }));
}
// If the server comes back with a newer page, reload so no tab keeps running old code.
let uiVersion = null;
async function checkVersion() {
  try {
    const c = await getJSON("/api/config");
    if (uiVersion && c.ui_version && c.ui_version !== uiVersion) location.reload();
    uiVersion = c.ui_version;
  } catch { /* server still starting */ }
}
function connect() {
  ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
  ws.onopen = checkVersion;
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "response") showResponse(msg.data);
    else if (msg.type === "transcript") { if (msg.text) addVisitor(msg.text); }
    else if (msg.type === "noise") showNoiseHint();
    else if (msg.type === "language") setLang(msg.lang);
    else if (msg.type === "banner") showBanner(msg.seconds);
    else if (msg.type === "session_end") resetVisitor(false);
    else if (msg.type === "presence") { body.dataset.presence = msg.present ? "yes" : "no"; setState(body.dataset.state); }
    else if (msg.type === "state" && !(msg.state === "listening" && speechSynthesis.speaking)) setState(msg.state);
    else if (msg.type === "error") console.warn("server:", msg.message);
    handlers.forEach((fn) => fn(msg));
  };
  ws.onclose = () => { $("#status-text").textContent = t("reconnecting"); setTimeout(connect, 1500); };
}

// `shown` is what the visitor sees in their language when the question sent is English (buttons).
export function ask(text, shown) {
  const q = text.trim();
  if (!q) return;
  stopSpeaking(); // a new question always interrupts the current answer
  addVisitor(shown || q);
  if (body.dataset.view === "welcome") setView("chat");
  sendRaw({ type: "ask", text: q });
  resetIdle();
}
// The visitor chose a language: switch the screen now; the server confirms and greets in it.
function chooseLanguage(lang) {
  stopSpeaking();
  setLang(lang);
  sendRaw({ type: "language", lang });
  if (body.dataset.view === "welcome") setView("chat");
  resetIdle();
}

let idleTimer;
const IDLE_MS = 120_000;
function resetIdle() { clearTimeout(idleTimer); idleTimer = setTimeout(() => resetVisitor(true), IDLE_MS); }
function resetVisitor(tellServer) {
  stopSpeaking();
  setLang("en"); // every new visitor starts in English with the picker on screen
  window.dispatchEvent(new CustomEvent("kiosk:reset"));
  $("#log").replaceChildren();
  route = null;
  body.dataset.presence = "no";
  if (tellServer) sendRaw({ type: "new_session" });
  setView("welcome");
  setState("idle");
}

// ---------------------------------------------------------------- speech out
// English uses the browser's own voice; Hindi and Kannada use natural voices from /api/tts,
// falling back to a browser voice for that language if the voice service is unreachable.
function browserVoice(lang) {
  const vs = speechSynthesis.getVoices();
  const code = { en: "en", hi: "hi", kn: "kn" }[lang] || "en";
  return vs.find((v) => v.lang === `${code}-IN`) || vs.find((v) => v.lang.startsWith(code)) || null;
}
speechSynthesis.onvoiceschanged = () => {};
let speechSeq = 0;
let currentAudio = null;
// Stop talking immediately (the visitor interrupted by tapping the mic or typing).
export function stopSpeaking() {
  speechSeq++;
  speechSynthesis.cancel();
  if (currentAudio) { currentAudio.pause(); currentAudio = null; }
  body.dataset.speaking = "no";
}
function speak(text, onEnd, lang = "en") {
  const mine = ++speechSeq;
  speechSynthesis.cancel();
  if (currentAudio) { currentAudio.pause(); currentAudio = null; }
  body.dataset.speaking = "yes";
  const done = () => {
    if (mine !== speechSeq) return; // interrupted or replaced by a newer answer
    currentAudio = null;
    body.dataset.speaking = "no";
    if (onEnd) onEnd();
  };
  const viaBrowser = () => {
    if (mine !== speechSeq) return;
    const v = browserVoice(lang);
    if (lang !== "en" && !v) { done(); return; } // no voice for this language: the text stays on screen
    const u = new SpeechSynthesisUtterance(text);
    if (v) u.voice = v;
    u.lang = v ? v.lang : "en-IN";
    u.rate = 0.98;
    u.onend = u.onerror = done;
    speechSynthesis.speak(u);
  };
  if (lang === "en") { viaBrowser(); return; }
  const audio = new Audio(`/api/tts?lang=${lang}&text=${encodeURIComponent(text)}`);
  currentAudio = audio;
  audio.onended = done;
  audio.onerror = () => { if (currentAudio === audio) { currentAudio = null; viaBrowser(); } };
  audio.play().catch(() => { if (currentAudio === audio) { currentAudio = null; viaBrowser(); } });
}

// ---------------------------------------------------------------- chat
const log = $("#log");
function addVisitor(text) {
  log.append(el("li", { class: "msg msg--visitor" },
    el("span", { class: "avatar", html: icon("user") }), el("div", { class: "bubble" }, text)));
  log.scrollTop = log.scrollHeight;
}
function addKiosk(text, card, handover = false) {
  log.append(el("li", { class: `msg msg--kiosk${handover ? " msg--handover" : ""}` },
    el("span", { class: "avatar", html: icon("building") }),
    el("div", { class: "msg-body" }, el("div", { class: "bubble" }, text), card || null)));
  log.scrollTop = log.scrollHeight;
}
function qrGrid(qr) {
  if (!qr || !qr.length) return null;
  return el("div", { class: "qr-grid" }, qr.map((q) => el("figure", { class: "qr" }, svgNode(q.svg), el("figcaption", {}, q.label))));
}
function goButton(label, view, iconName) {
  return el("button", { class: "pill-btn pill-btn--gold", type: "button", onclick: () => setView(view) },
    iconNode(iconName), label);
}

const inlineCard = {
  timings(d, r) {
    if (d.offices && d.library) {
      const row = (label, x) => el("div", { class: "hours-row" }, iconNode("clock"), el("span", {}, label),
        el("span", { class: `badge ${x.today === "closed" ? "badge--closed" : "badge--open"}` }, x.today === "closed" ? t("closed_today") : x.today));
      return el("div", { class: "card answer-card" }, el("h3", {}, iconNode("building"), t("today_in_block")),
        row(t("offices"), d.offices), row(t("library"), d.library));
    }
    const cls = d.is_open ? "open" : d.on_lunch ? "lunch" : "closed";
    const label = t(d.is_open ? "open_now" : d.on_lunch ? "lunch_break" : "closed_now");
    const nameKey = { offices: "office_hours", library: "central_library", services: "hours" }[d.name];
    const name = nameKey ? t(nameKey) : d.name;
    const rules = d.rules || {};
    const t12 = (hhmm) => { const [h, m] = hhmm.split(":").map(Number); const hr = h % 12 || 12; return `${hr}${m ? ":" + String(m).padStart(2, "0") : ""} ${h < 12 ? "am" : "pm"}`; };
    const span = (x) => (Array.isArray(x) ? `${t12(x[0])} – ${t12(x[1])}` : x === "closed" ? t("closed") : t("same_as_week"));
    const rows = [
      [t("mon_sat"), span(rules.weekday)],
      ...(rules.lunch ? [[t("lunch_break"), span(rules.lunch)]] : []),
      [t("third_saturday"), span(rules.third_saturday)],
      [t("sunday"), span(rules.sunday)],
      [t("vacation"), span(rules.vacation)],
      [t("public_holidays"), t("closed")],
    ];
    const table = el("div", {}, rows.map(([k, v]) => el("div", { class: "hours-row" }, iconNode("calendar"), el("span", {}, k), el("b", {}, v))));
    const info = el("div", {}, el("h3", {}, iconNode("book"), name),
      el("p", {}, el("span", { class: `badge badge--${cls}` }, label), ` ${t("today")} `, d.today), table,
      d.verified === false ? el("p", { class: "warn" }, t("hours_unconfirmed")) : null,
      el("div", { class: "row-actions" },
        d.name === "library" || d.name === "Library"
          ? el("button", { class: "pill-btn pill-btn--gold", type: "button", onclick: () => ask("Where is the library?", t("view_on_map")) }, iconNode("pin"), t("view_on_map"))
          : null));
    const isLibrary = /library/i.test(d.name);
    const q = (r.qr || [])[0];
    return el("div", { class: "card answer-card" },
      isLibrary ? el("div", { class: "answer-media" }, el("img", { src: "/static/img/library.jpg", alt: "" }), info) : info,
      q ? el("figure", { class: "qr qr--wide" }, svgNode(q.svg), el("figcaption", {}, t("scan_library"))) : null);
  },
  text(d, r) {
    if (d.library_link) {
      const q = (r.qr || [])[0];
      return el("div", { class: "card answer-card" }, el("div", { class: "answer-media" },
        el("img", { src: "/static/img/library.jpg", alt: "" }),
        el("div", {}, el("h3", {}, iconNode("book"), t("central_library")),
          el("p", {}, d.topic ? t("library_topic", { topic: d.topic }) : t("library_site")),
          el("p", { class: "note" }, d.library_link.replace(/^https?:\/\//, "")),
          el("div", { class: "row-actions" },
            el("button", { class: "pill-btn pill-btn--gold", type: "button", onclick: () => ask("What are the library timings?", t("library_timings")) }, iconNode("clock"), t("library_timings")),
            el("button", { class: "pill-btn", type: "button", onclick: () => ask("Where is the library?", t("view_on_map")) }, iconNode("pin"), t("view_on_map"))))),
        q ? el("figure", { class: "qr qr--wide" }, svgNode(q.svg), el("figcaption", {}, t("scan_library"))) : null);
    }
    const passages = (d.passages || []).map((p) => el("li", {}, `${p.source}: ${p.text}`));
    return passages.length || (r.qr && r.qr.length)
      ? el("div", { class: "card answer-card" }, qrGrid(r.qr),
        passages.length ? el("details", {}, el("summary", {}, t("answer_source")), el("ul", { class: "note" }, passages)) : null)
      : null;
  },
  handover(d, r) {
    return el("div", { class: "card answer-card" }, el("h3", {}, iconNode("alert"), t("check_reception")),
      el("p", { class: "note" }, t("reception_note")), qrGrid(r.qr),
      r.maps && r.maps.length ? el("div", { class: "row-actions" }, goButton(t("route_health"), "navigate", "pin")) : null);
  },
  clarify(d) {
    const labels = d.option_labels || d.options;
    return el("div", { class: "options" }, d.options.map((o, i) =>
      el("button", { class: "pill-btn", type: "button", onclick: () => onOption(o, labels[i]) }, labels[i] || o)));
  },
  contacts(d, r) {
    const events = (d.events || []).map((e) => el("div", { class: "hours-row" }, iconNode("calendar"), el("span", {}, e.name), el("b", {}, e.when)));
    return el("div", { class: "card answer-card" }, events.length ? el("div", {}, events) : null, qrGrid(r.qr),
      el("div", { class: "row-actions" }, goButton(t("all_contacts"), "contacts", "phone")));
  },
};

const OPTION_TEXT = {
  "Find a place": null, "Courses & fees": null, Timings: "What are the office timings?",
  Contacts: null, Events: null, "Talk to a person": "I want to talk to a person",
};
function onOption(o, label) {
  const view = { "Find a place": "navigate", "Courses & fees": "courses", Contacts: "contacts", Events: "events" }[o];
  if (view) { setView(view); return; }
  ask(OPTION_TEXT[o] || o, label);
}

// ---------------------------------------------------------------- responses
function showResponse(r) {
  window.dispatchEvent(new CustomEvent("kiosk:answer")); // mic goes off while an answer is shown
  const kind = r.card.kind;
  const d = r.card.data;
  let next = "answering";
  if (r.intent === "greeting") {
    body.dataset.presence = "yes";
    addKiosk(r.speech, inlineCard.clarify(d));
    if (body.dataset.view !== "welcome") setView("chat");
  } else if (kind === "map") {
    renderRoute(r);
    addKiosk(r.speech, el("div", { class: "row-actions" }, goButton(t("show_route"), "navigate", "pin")));
    setView("navigate");
    next = "navigating";
  } else if (kind === "course_list") {
    const listDept = d.department || "";
    const listLevel = d.level || "All";
    addKiosk(r.speech, el("div", { class: "row-actions" },
      el("button", { class: "pill-btn pill-btn--gold", type: "button", onclick: () => openCourses(listDept, null, listLevel) },
        iconNode("cap"), t("see_programmes"))));
    openCourses(listDept, null, listLevel);
  } else if (kind === "course" || kind === "fees") {
    const cDept = d.department || null;
    const cId = d.course_id;
    const fees = kind === "fees";
    addKiosk(r.speech, el("div", { class: "row-actions" },
      el("button", { class: "pill-btn pill-btn--gold", type: "button", onclick: () => openCourses(cDept, cId, "All", fees) },
        iconNode("cap"), t("programme_details"))), false);
    openCourses(cDept, cId, "All", fees);
  } else if (kind === "events") {
    addKiosk(r.speech, el("div", { class: "row-actions" }, goButton(t("open_calendar"), "events", "calendar")));
    const first = d.items && d.items[0] && d.items[0].start;
    if (first) { const [y, m] = first.split("-").map(Number); cal.year = y; cal.month = m; }
    cal.highlight = (d.items || []).map((i) => i.name);
    loadCalendar(cal.year, cal.month);
    setView("events");
  } else {
    const fn = inlineCard[kind] || inlineCard.text;
    addKiosk(r.speech, fn(d, r), !!r.handover_reason);
    if (r.handover_reason === "urgent" && r.maps && r.maps.length) renderRoute({ ...r, card: { data: { ...d, target_names: ["Health Centre"] } } });
    setView("chat");
  }
  setState(next);
  speak(r.speech, () => setState(r.handover_reason ? "handover" : "listening"), r.lang || getLang());
  resetIdle();
}

// ---------------------------------------------------------------- navigate
let route = null;
const FLOOR_IDS = ["B", "G", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"];
async function showMap(floor) {
  for (const b of $$(".floor-btn")) b.classList.toggle("is-active", b.dataset.floor === floor);
  const frame = $("#map-frame");
  const fromRoute = route && route.maps.find((m) => m.floor === floor);
  if (fromRoute) { frame.replaceChildren(svgNode(fromRoute.svg)); return; }
  const hl = route ? route.card.data.targets.join(",") : "";
  const r = await fetch(`/api/floor/${floor}.svg?highlight=${encodeURIComponent(hl)}`);
  frame.replaceChildren(svgNode(await r.text()));
}
function floorPicker(onRoute, active) {
  $("#floor-picker").replaceChildren(...FLOOR_IDS.map((f) => el("button", {
    class: `floor-btn${onRoute.includes(f) ? " on-route" : ""}`, type: "button", "data-floor": f,
    "aria-label": f === "B" ? t("basement") : f === "G" ? t("ground_floor") : t("floor_n", { n: f }), onclick: () => showMap(f),
  }, f)));
  showMap(active);
}
function renderRoute(r) {
  route = r;
  const d = r.card.data;
  const name = (d.target_names || [])[0] || t("your_destination");
  $("#nav-title").textContent = t("route_to", { name: name.replace(/\s*[,(].*$/, "") });
  $("#nav-lead").textContent = r.speech;
  const floors = r.maps.map((m) => m.floor);
  const dest = r.maps.length ? r.maps[Math.min(1, r.maps.length - 1)] : null;
  const steps = (d.steps || []).slice(0, -1);
  const last = (d.steps || []).slice(-1)[0] || "";
  const stepIcon = (s) => (/lift|stairs/i.test(s) ? "lift" : /corridor|turn/i.test(s) ? "turn" : "navigate");
  $("#nav-side").replaceChildren(
    el("ol", { class: "timeline" },
      el("li", { class: "step step--start" }, el("span", { class: "step-icon", html: icon("pin") }), el("span", {}, el("b", {}, t("start_reception")), t("ground_floor"))),
      steps.map((s) => el("li", { class: "step" }, el("span", { class: "step-icon", html: icon(stepIcon(s)) }), el("span", {}, s))),
      el("li", { class: "step step--end" }, el("span", { class: "step-icon", html: icon("flag") }),
        el("span", {}, el("b", {}, t("destination", { name })), dest ? dest.title : "", last ? el("span", { class: "note" }, el("br"), last) : null))),
    el("p", { class: "nav-meta" }, `${t("floors_on_route")} ${floors.map((f) => (f === "G" ? t("ground") : f === "B" ? t("basement") : f)).join(" → ")}`),
    el("div", { class: "row-actions" }, el("button", { class: "pill-btn", type: "button", onclick: () => { route = null; showPlaceBrowser(); } }, iconNode("search"), t("find_another"))));
  floorPicker(floors, dest ? dest.floor : "G");
}
let places = null;
async function showPlaceBrowser() {
  $("#nav-title").textContent = t("find_place");
  $("#nav-lead").textContent = t("find_lead");
  places = places || (await getJSON("/api/places"));
  const input = el("input", { placeholder: t("search_places"), "aria-label": t("search_places") });
  const groups = el("div", { class: "place-groups" });
  const draw = () => {
    const q = input.value.trim().toLowerCase();
    const byFloor = new Map();
    for (const p of places) {
      if (q && !p.name.toLowerCase().includes(q)) continue;
      if (!byFloor.has(p.floor_name)) byFloor.set(p.floor_name, []);
      byFloor.get(p.floor_name).push(p);
    }
    groups.replaceChildren(...[...byFloor].map(([floor, list]) => el("section", {}, el("h3", {}, floor),
      list.map((p) => el("button", { class: "place-btn", type: "button", onclick: () => ask(`Where is the ${p.name}?`) }, p.name)))));
    if (!byFloor.size) groups.replaceChildren(el("p", { class: "note" }, t("no_place")));
  };
  input.addEventListener("input", draw);
  draw();
  $("#nav-side").replaceChildren(el("label", { class: "place-search" }, iconNode("search"), input), groups);
  floorPicker([], "G");
}

// ---------------------------------------------------------------- courses
const courses = { loaded: false, dept: "Department of Computer Science", level: "All", query: "", items: [], selected: null, showFees: false };
let departments = null;
async function loadCourses(dept) {
  departments = departments || (await getJSON("/api/departments"));
  const select = $("#dept-select");
  if (!select.options.length) {
    fillDepartments(select);
    select.addEventListener("change", () => { courses.selected = null; loadCourses(select.value); });
  }
  if (dept !== undefined && dept !== null) courses.dept = dept;
  select.value = courses.dept;
  courses.items = await getJSON(courses.dept ? `/api/courses?department=${encodeURIComponent(courses.dept)}` : "/api/courses");
  courses.loaded = true;
  drawCourses();
  if (!courses.selected && courses.items.length) selectCourse(courses.items[0].id);
}
function fillDepartments(select) {
  const inBlock = departments.filter((d) => d.floor_name);
  const outside = departments.filter((d) => !d.floor_name);
  const opt = (d) => el("option", { value: d.name }, d.name);
  select.replaceChildren(el("option", { value: "" }, t("all_departments")),
    el("optgroup", { label: t("in_block") }, inBlock.map(opt)), el("optgroup", { label: t("other_depts") }, outside.map(opt)));
  select.value = courses.dept;
}
function drawCourses() {
  const dept = departments.find((d) => d.name === courses.dept);
  $("#course-count").textContent = !courses.dept
    ? t("count_campus", { n: courses.items.length })
    : t("count_dept", { n: courses.items.length }) + (dept && dept.floor_name ? ` · ${dept.floor_name}` : ` · ${t("not_in_block")}`);
  $("#level-chips").replaceChildren(...["All", "UG", "PG", "PhD"].map((lv) => el("button", {
    class: `chip${courses.level === lv ? " is-active" : ""}`, type: "button", "aria-pressed": courses.level === lv,
    onclick: () => { courses.level = lv; drawCourses(); },
  }, lv === "All" ? t("level_all") : lv)));
  const q = courses.query.toLowerCase();
  const list = courses.items.filter((c) => (courses.level === "All" || c.level === courses.level) && (!q || c.name.toLowerCase().includes(q)));
  const levelName = { UG: t("undergraduate"), PG: t("postgraduate"), PhD: t("doctoral") };
  $("#course-list").replaceChildren(...(list.length ? list.map((c) => el("li", {}, el("button", {
    class: `course-item${courses.selected === c.id ? " is-active" : ""}`, type: "button", onclick: () => selectCourse(c.id),
  }, el("span", { class: "ic", html: icon("cap") }), el("span", {}, el("b", {}, c.name), el("small", {}, [levelName[c.level] || c.level, c.duration, courses.dept ? null : c.department].filter(Boolean).join(" • "))),
  iconNode("right")))) : [el("li", { class: "empty" }, t("no_match"))]));
  // The details panel must always show a programme from the visible list.
  if (!list.length) {
    courses.selected = null;
    $("#course-detail").replaceChildren(el("p", { class: "empty" }, t("none_selected")));
  } else if (!list.some((c) => c.id === courses.selected)) {
    selectCourse(list[0].id);
  }
}
async function selectCourse(id, showFees = false) {
  courses.selected = id;
  courses.showFees = showFees;
  drawCourses();
  const data = await getJSON(`/api/course/${id}`);
  if (courses.selected !== id) return; // a newer selection arrived while this one loaded
  const c = data.course;
  const f = data.fees;
  const desc = el("p", { class: "desc clamped" }, c.description || t("no_description"));
  const years = Object.keys(f.years || {});
  const cats = years.length ? Object.keys(f.years[years[0]]) : [];
  const feeTable = el("div", { hidden: !showFees },
    el("table", { class: "fees" }, el("thead", {}, el("tr", {}, el("th", {}, t("category")), years.map((y) => el("th", {}, t("year_n", { n: y }))))),
      el("tbody", {}, cats.map((k) => el("tr", {}, el("th", {}, k), years.map((y) => el("td", {}, f.years[y][k])))))),
    el("p", { class: "note" }, t("registration_fee", { fee: f.registration_fee, year: f.academic_year })));
  const dept = departments && departments.find((d) => d.name === c.department);
  $("#course-detail").replaceChildren(
    el("div", { class: "detail-hero" }, el("h2", {}, c.name)),
    el("div", { class: "detail-body" },
      el("ul", { class: "facts" },
        c.duration ? el("li", { html: icon("hourglass") + c.duration }) : null,
        el("li", { html: icon("cap") + c.level }),
        c.semesters ? el("li", { html: icon("calendar") + c.semesters }) : null,
        el("li", {}, iconNode("pin"), dept && dept.floor_name ? dept.floor_name : t("not_in_block_cap"))),
      desc, feeTable,
      c.verified ? null : el("p", { class: "warn" }, t("unconfirmed_name")),
      el("div", { class: "row-actions" },
        el("button", { class: "btn btn--solid", type: "button", onclick: (e) => { desc.classList.toggle("clamped"); e.currentTarget.lastChild.textContent = desc.classList.contains("clamped") ? t("view_details") : t("show_less"); } }, iconNode("right"), t("view_details")),
        el("button", { class: "btn btn--ghost", type: "button", onclick: () => { feeTable.hidden = !feeTable.hidden; } }, iconNode("book"), t("fee_structure"))),
      qrGrid(data.qr)));
}
function openCourses(dept, courseId, level, showFees = false) {
  // dept: a department name, "" for every department, or null to use the course's own.
  courses.level = level || "All";
  courses.query = "";
  $("#course-search").value = "";
  if (!courseId) courses.selected = null;
  courses.loaded = true; // this function does the loading; skip the screen's default (Computer Science) load
  setView("courses");
  const go = async () => {
    await loadCourses(dept === null ? courses.dept : dept);
    if (courseId) await selectCourse(courseId, showFees);
  };
  if (courseId && !dept) {
    getJSON(`/api/course/${courseId}`).then((d) => { courses.dept = d.course.department; go(); });
  } else go();
}
$("#course-search").addEventListener("input", (e) => { courses.query = e.target.value; drawCourses(); });

// ---------------------------------------------------------------- events
const today = new Date();
const cal = { loaded: false, year: today.getFullYear(), month: today.getMonth() + 1, highlight: [] };
const EVENT_ICON = { open_day: "users", fest: "star", ceremony: "trophy", admissions: "cap", exam: "book", other: "calendar" };
async function loadCalendar(year, month) {
  const data = await getJSON(`/api/calendar?year=${year}&month=${month}`);
  cal.loaded = true; cal.year = year; cal.month = month;
  $("#cal-title").textContent = new Date(year, month - 1, 1).toLocaleDateString(locale(), { month: "long", year: "numeric" });
  const iso = (d) => `${year}-${String(month).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  const dow = new Intl.DateTimeFormat(locale(), { weekday: "short" });
  const cells = [1, 2, 3, 4, 5, 6, 7].map((d) => el("span", { class: "dow" }, dow.format(new Date(2024, 0, d)))); // 1 Jan 2024 was a Monday
  for (let i = 0; i < data.first_weekday; i++) cells.push(el("span"));
  for (let d = 1; d <= data.days; d++) {
    const day = iso(d);
    const evs = data.events.filter((e) => e.start <= day && e.end >= day);
    const multi = evs.some((e) => e.start !== e.end);
    const hol = data.holidays.some((h) => h.date === day);
    const isToday = year === today.getFullYear() && month === today.getMonth() + 1 && d === today.getDate();
    const cls = ["cal-day", evs.length ? (multi ? "multi" : "event") : "", hol ? "holiday" : "", isToday ? "today" : ""].join(" ");
    const label = [...evs.map((e) => e.name), ...data.holidays.filter((h) => h.date === day).map((h) => t("holiday_prefix", { name: h.name }))].join(", ");
    cells.push(el("span", { class: cls, title: label || null, "aria-label": `${d}${label ? ": " + label : ""}` }, d));
  }
  $("#cal-grid").replaceChildren(...cells);
  const fmt = (s) => new Date(s + "T00:00").toLocaleDateString(locale(), { day: "numeric", month: "long" });
  const items = [
    ...data.events.map((e) => ({ when: e.start === e.end ? fmt(e.start) : `${fmt(e.start)} – ${fmt(e.end)}`, name: e.name, kind: e.kind, sort: e.start })),
    ...data.holidays.map((h) => ({ when: fmt(h.date), name: t("holiday_prefix", { name: h.name }), kind: "holiday", sort: h.date })),
  ].sort((a, b) => a.sort.localeCompare(b.sort));
  $("#event-list").replaceChildren(...(items.length ? items.map((it) => el("li", { class: `event-item${it.kind === "holiday" ? " holiday" : ""}` },
    el("span", { class: "ic", html: icon(it.kind === "holiday" ? "flag" : EVENT_ICON[it.kind] || "calendar") }),
    el("span", {}, el("b", {}, it.when), it.name))) : [el("li", { class: "empty" }, data.valid ? t("nothing_month") : t("calendar_missing"))]));
}
$("#cal-prev").addEventListener("click", () => { const m = cal.month === 1 ? 12 : cal.month - 1; loadCalendar(cal.month === 1 ? cal.year - 1 : cal.year, m); });
$("#cal-next").addEventListener("click", () => { const m = cal.month === 12 ? 1 : cal.month + 1; loadCalendar(cal.month === 12 ? cal.year + 1 : cal.year, m); });

// ---------------------------------------------------------------- contacts
let contactsLoaded = false;
async function loadContacts() {
  const items = await getJSON("/api/contacts");
  contactsLoaded = true;
  const ic = { phone: "phone", email: "mail", url: "link" };
  $("#contact-grid").replaceChildren(...items.map((c) => el("article", { class: "card contact-card" },
    el("div", {}, el("span", { class: "ic", html: icon(ic[c.kind]) }), el("b", {}, c.label), el("span", { class: "val" }, c.kind === "url" ? c.value.replace(/^https?:\/\//, "") : c.value)),
    el("div", { class: "qr-box", html: c.qr }))));
}

// ---------------------------------------------------------------- banner, clock, boot
function showNoiseHint() {
  addKiosk(t("noise_hint"), null);
  setState("idle");
}
function showBanner(seconds) {
  const b = $("#banner");
  b.hidden = false;
  clearTimeout(showBanner.t);
  showBanner.t = setTimeout(() => { b.hidden = true; }, seconds * 1000);
}
function drawShortcuts() {
  const tiles = [["pin", "tile_find", () => setView("navigate"), true], ["cap", "tile_courses", () => setView("courses")],
    ["calendar", "tile_events", () => setView("events")], ["clock", "tile_timings", () => ask("What are the office timings?", t("tile_timings"))],
    ["phone", "tile_contacts", () => setView("contacts")], ["users", "tile_person", () => ask("I want to talk to a person", t("tile_person"))]];
  $("#tiles").replaceChildren(...tiles.map(([i, key, fn, primary]) => el("button", { class: `tile${primary ? " tile--primary" : ""}`, type: "button", onclick: fn }, iconNode(i), t(key))));
  const quick = [["pin", "quick_dir", "navigate"], ["cap", "quick_prog", "courses"], ["calendar", "quick_cal", "events"], ["phone", "quick_contacts", "contacts"]];
  $("#quick").replaceChildren(...quick.map(([i, key, view]) => el("button", { class: "qa", type: "button", onclick: () => setView(view) }, iconNode(i), el("span", {}, t(key)), iconNode("right"))));
}
// Redraw everything on screen in the newly chosen language (the chat history stays as it was).
function relabel() {
  drawShortcuts();
  setState(body.dataset.state);
  const hint = $(".mic-hint");
  if (hint) hint.textContent = t(body.dataset.mic === "on" ? "mic_hint_on" : "mic_hint_off");
  if (departments && $("#dept-select").options.length) fillDepartments($("#dept-select"));
  if (courses.loaded && departments) { drawCourses(); if (courses.selected) selectCourse(courses.selected, courses.showFees); }
  if (cal.loaded) loadCalendar(cal.year, cal.month);
  if (body.dataset.view === "navigate") { if (route) renderRoute(route); else showPlaceBrowser(); }
  tick();
}
const tick = () => { $("#clock").textContent = new Date().toLocaleTimeString(locale(), { hour: "2-digit", minute: "2-digit" }); };
function boot() {
  hydrateIcons();
  applyStatic();
  drawShortcuts();
  for (const b of $$("button[data-lang]")) b.addEventListener("click", () => chooseLanguage(b.dataset.lang));
  window.addEventListener("kiosk:lang", relabel);
  for (const b of $$(".nav-item")) b.addEventListener("click", () => setView(b.dataset.go));
  $("#ask-input").addEventListener("input", () => { if (body.dataset.speaking === "yes") stopSpeaking(); });
  $("#ask").addEventListener("submit", (e) => { e.preventDefault(); const i = $("#ask-input"); ask(i.value); i.value = ""; });
  $("#new-visitor").addEventListener("click", () => resetVisitor(true));
  window.addEventListener("kiosk:mic", (e) => {
    const hint = $(".mic-hint");
    if (hint) hint.textContent = t(e.detail.on ? "mic_hint_on" : "mic_hint_off");
    if (e.detail.on) { setState("listening"); if (body.dataset.view === "welcome") setView("chat"); }
    else if (body.dataset.state === "listening") setState("idle");
  });
  tick(); setInterval(tick, 15_000);
  connect();
}
boot();

export { setState };
