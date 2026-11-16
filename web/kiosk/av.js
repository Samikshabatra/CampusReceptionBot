// Camera + microphone for the kiosk. Frames and audio go to the server; nothing is stored.
import { sendRaw, stopSpeaking } from "/static/app.js?v=9";

const body = document.body;
const TARGET_RATE = 16000;

async function loadConfig() {
  try {
    const r = await fetch("/api/config");
    return await r.json();
  } catch {
    return { vision: { frame_interval_ms: 200 }, speech: { vad_rms_threshold: 0.015, silence_ms: 900, min_speech_ms: 300, max_utterance_s: 10 } };
  }
}

function toBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(bin);
}

// ---------- camera: ~5 small JPEG frames per second for visitor detection ----------
async function startCamera(intervalMs) {
  const video = document.querySelector("#camera");
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 320, height: 240 }, audio: false });
    video.srcObject = stream;
    await video.play();
  } catch (e) {
    body.dataset.camera = "off";
    console.warn("camera unavailable:", e.message);
    return;
  }
  body.dataset.camera = "on";
  const canvas = document.createElement("canvas");
  canvas.width = 320;
  canvas.height = 240;
  const g = canvas.getContext("2d");
  setInterval(() => {
    if (video.readyState < 2) return;
    g.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(async (blob) => {
      if (!blob) return;
      sendRaw({ type: "frame", jpeg: toBase64(await blob.arrayBuffer()) });
    }, "image/jpeg", 0.6);
  }, intervalMs);
}

// ---------- microphone: energy-based voice detection, one utterance per message ----------
const WORKLET = `
class Tap extends AudioWorkletProcessor {
  process(inputs) { const ch = inputs[0][0]; if (ch) this.port.postMessage(ch.slice(0)); return true; }
}
registerProcessor("tap", Tap);`;

function downsample(chunk, fromRate) {
  if (fromRate === TARGET_RATE) return chunk;
  const ratio = fromRate / TARGET_RATE;
  const out = new Float32Array(Math.floor(chunk.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(chunk.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = start; j < end; j++) sum += chunk[j];
    out[i] = sum / Math.max(1, end - start);
  }
  return out;
}

// The microphone is opened ONLY while the visitor has switched it on, and fully released
// (tracks stopped, so the browser's recording indicator goes off) when switched off.
function startMic(cfg) {
  let on = false; // audio is flowing
  let wanted = false; // what the visitor last asked for (drives the button instantly)
  let ctx = null;
  let node = null;
  let stream = null;
  let source = null;
  let collecting = false;
  let chunks = [];
  let speechMs = 0;
  let silenceMs = 0;
  let noiseFloor = cfg.vad_rms_threshold / 2; // learned from the room while nobody speaks
  body.dataset.mic = "off";

  const resetUtterance = () => { collecting = false; chunks = []; speechMs = 0; silenceMs = 0; };
  const flush = () => {
    const total = chunks.reduce((n, c) => n + c.length, 0);
    const all = new Float32Array(total);
    let off = 0;
    for (const c of chunks) { all.set(c, off); off += c.length; }
    const spoke = speechMs >= cfg.min_speech_ms;
    if (spoke) sendRaw({ type: "audio", pcm: toBase64(all.buffer) });
    resetUtterance();
    if (spoke) turnOff(); // one question per tap; tap again to ask the next one
  };
  const announce = () => {
    body.dataset.mic = wanted ? "on" : "off";
    for (const b of document.querySelectorAll("button[data-mic]")) {
      b.setAttribute("aria-pressed", String(wanted));
      b.setAttribute("aria-label", wanted ? "Microphone on. Tap to turn it off" : "Microphone off. Tap to speak");
      b.title = wanted ? "Listening. Tap to turn the microphone off" : "Tap to turn the microphone on";
      const label = b.querySelector(".mic-label");
      if (label) label.textContent = wanted ? "Listening… tap to stop" : "Tap to speak";
    }
    window.dispatchEvent(new CustomEvent("kiosk:mic", { detail: { on: wanted } }));
  };
  const releaseMic = () => {
    if (source) { source.disconnect(); source = null; }
    if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
  };

  async function turnOn() {
    wanted = true;
    announce(); // the button switches on immediately
    try {
      if (!ctx) {
        ctx = new AudioContext();
        const url = URL.createObjectURL(new Blob([WORKLET], { type: "application/javascript" }));
        await ctx.audioWorklet.addModule(url);
        node = new AudioWorkletNode(ctx, "tap");
        node.port.onmessage = onAudio;
      }
      const s = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 } });
      if (!wanted) { s.getTracks().forEach((t) => t.stop()); return; } // switched off while opening
      releaseMic(); // never keep two microphones open
      stream = s;
      source = ctx.createMediaStreamSource(stream);
      source.connect(node);
      await ctx.resume();
      on = wanted;
      if (!wanted) releaseMic();
    } catch (e) {
      on = false;
      wanted = false;
      body.dataset.micError = "yes";
      console.warn("microphone unavailable:", e.message);
      announce();
    }
    resetUtterance();
  }
  function turnOff() {
    wanted = false;
    on = false;
    resetUtterance();
    releaseMic();
    announce(); // one click is always enough
  }
  function onAudio(ev) {
    // Hear nothing while the mic is off, while the kiosk is talking, or while it is thinking.
    if (!on || body.dataset.speaking === "yes" || body.dataset.state === "thinking") { if (collecting) resetUtterance(); return; }
    const chunk = downsample(ev.data, ctx.sampleRate);
    const ms = (chunk.length / TARGET_RATE) * 1000;
    let sq = 0;
    for (const v of chunk) sq += v * v;
    const rms = Math.sqrt(sq / Math.max(1, chunk.length));
    // Speech must stand out from the room's own noise (fans, chatter), not just pass a fixed level.
    const loud = rms >= Math.max(cfg.vad_rms_threshold, noiseFloor * 3);
    if (!loud && !collecting) noiseFloor = 0.95 * noiseFloor + 0.05 * rms;
    if (loud) { collecting = true; speechMs += ms; silenceMs = 0; }
    else if (collecting) silenceMs += ms;
    if (!collecting) return;
    chunks.push(chunk);
    if (silenceMs >= cfg.silence_ms || speechMs + silenceMs >= cfg.max_utterance_s * 1000) flush();
  }

  for (const button of document.querySelectorAll("button[data-mic]")) {
    button.addEventListener("click", () => {
      // Tapping the mic while the kiosk is talking interrupts it and starts listening.
      if (body.dataset.speaking === "yes") { stopSpeaking(); if (!wanted) turnOn(); return; }
      if (wanted) turnOff(); else turnOn();
    });
  }
  // A new visitor always starts with the microphone off.
  window.addEventListener("kiosk:reset", () => { if (wanted) turnOff(); });
  window.addEventListener("kiosk:answer", () => { if (wanted) turnOff(); });
  announce();
}

const cfg = await loadConfig();
startCamera(cfg.vision.frame_interval_ms);
startMic(cfg.speech);
