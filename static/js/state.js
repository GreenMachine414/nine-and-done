// Client state + API layer.
import { toast } from "./ui.js";

const qsSid = new URLSearchParams(location.search).get("sid");
if (qsSid) localStorage.setItem("nd_sid", qsSid);
export const S = {
  sid: localStorage.getItem("nd_sid") ? +localStorage.getItem("nd_sid") : null,
  L: null,
  ui: { rosterTab: "lineup", statsSort: "pts", statsTeam: "all", tradeTid: null, give: { players: [], picks: [] }, get: { players: [], picks: [] }, tradeEval: null, tradeTab: "build", draftSort: "rank", faSort: "ovr", schedDay: null },
};
export const hooks = { render: () => {} };
export const ACT = {};   // data-act handlers:  ACT[name](el, event)
export const SEG = {};   // segmented control handlers: SEG[name](value)

// Anonymous per-browser id: your leagues are tied to this browser (no account needed).
function ownerId() {
  let o = localStorage.getItem("nd_owner");
  if (!o) {
    o = (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`).replace(/[^A-Za-z0-9_-]/g, "");
    localStorage.setItem("nd_owner", o);
  }
  return o;
}

export async function api(path, body, method) {
  const headers = { "X-ND-Owner": ownerId() };
  if (body) headers["Content-Type"] = "application/json";
  const res = await fetch(`/api/${path}`, {
    method: method || (body ? "POST" : "GET"),
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({ error: "Bad response" }));
  if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

let busyEl = null;
function busy(on, label = "SIMULATING") {
  if (on) {
    busyEl = document.createElement("div");
    busyEl.className = "busy";
    busyEl.innerHTML = `<div class="loader">${label}</div>`;
    document.body.appendChild(busyEl);
  } else if (busyEl) { busyEl.remove(); busyEl = null; }
}

// ---- optimistic sync: the caller has ALREADY applied the change to S.L and re-rendered.
// Requests go out in order in the background; the reply is tiny. On failure we resync from the server.
let bgChain = Promise.resolve();
export function sync(type, payload = {}) {
  bgChain = bgChain
    .then(() => api(`s/${S.sid}/act`, { type, ...payload, lite: true }))
    .catch(async (e) => {
      toast(e.message, true);
      try { await loadState(); hooks.render(); } catch (_) { /* offline */ }
    });
  return bgChain;
}
// Server decides the outcome, but only a small result comes back (caller patches S.L itself).
export async function actLite(type, payload = {}) {
  await bgChain;
  const r = await api(`s/${S.sid}/act`, { type, ...payload, lite: true });
  return r.result;
}
// Read-only server question (no state comes back, nothing is saved).
export async function query(type, payload = {}) {
  await bgChain;
  const r = await api(`s/${S.sid}/act`, { type, ...payload });
  return r.result;
}

export async function act(type, payload = {}, { quiet = false, label, rerender = true } = {}) {
  await bgChain;   // never race a pending background save
  const t = setTimeout(() => busy(true, label), 180);
  try {
    const r = await api(`s/${S.sid}/act`, { type, ...payload });
    S.L = r.state;
    applyTheme();
    if (rerender) hooks.render();
    return r.result;
  } catch (e) {
    if (!quiet) toast(e.message, true);
    throw e;
  } finally {
    clearTimeout(t);
    busy(false);
  }
}

export async function loadState() {
  S.L = await api(`s/${S.sid}/state`);
  applyTheme();
  return S.L;
}

export function applyTheme() {
  const t = S.L && S.L.teams[S.L.user];
  const r = document.documentElement.style;
  if (!t) { r.removeProperty("--acc"); r.removeProperty("--acc2"); return; }
  r.setProperty("--acc", t.c1);
  r.setProperty("--acc2", t.c2);
}

// ---- selectors
const PSEUDO = {
  "-1": { tid: -1, abbr: "FA", city: "Free", name: "Agent", c1: "#8d95a7", c2: "#1a1d24", shape: "circle", glyph: "", arena: "", w: 0, l: 0, hist: [], lineup: [], strategy: {} },
  "-2": { tid: -2, abbr: "DFT", city: "Draft", name: "Prospect", c1: "#d4ff3a", c2: "#1a1d24", shape: "circle", glyph: "", arena: "", w: 0, l: 0, hist: [], lineup: [], strategy: {} },
  "100": { tid: 100, abbr: "VLT", city: "Team", name: "Volt", c1: "#d4ff3a", c2: "#1d2a0c", shape: "hex", glyph: "bolt", arena: "All-Star Weekend", w: 0, l: 0, hist: [], lineup: [], strategy: {} },
  "101": { tid: 101, abbr: "FLR", city: "Team", name: "Flare", c1: "#ff5d3a", c2: "#3a1206", shape: "shield", glyph: "flame", arena: "All-Star Weekend", w: 0, l: 0, hist: [], lineup: [], strategy: {} },
};
export const T = (tid) => S.L.teams[tid] || PSEUDO[String(tid)] || PSEUDO["-1"];
export const Pl = (pid) => S.L.players[String(pid)];
export const me = () => S.L.teams[S.L.user];
export const roster = (tid) => Object.values(S.L.players).filter((p) => p.tid === tid);
export const lineupOf = (tid) => {
  const ids = new Set(roster(tid).map((p) => p.id));
  const lu = T(tid).lineup.filter((i) => ids.has(i));
  const rest = roster(tid).filter((p) => !lu.includes(p.id)).sort((a, b) => b.ovr - a.ovr).map((p) => p.id);
  return [...lu, ...rest].map(Pl);
};
export const seasonKey = (po = false) => `${S.L.season}${po ? "p" : ""}`;
export const recordStr = (t) => `${t.w}-${t.l}`;
export const payroll = (tid) => S.L.derived.payroll[tid];
export function nextGame() {
  const L = S.L;
  if (L.phase === "regular") {
    const m = L.schedule[L.day]?.find((g) => g.h === L.user || g.a === L.user);
    return m ? { home: m.h, away: m.a, label: `Game ${L.day + 1} of ${L.consts.days}` } : null;
  }
  if (L.phase === "playoffs") {
    const s = L.playoffs.series.find((s) => s.winner === null && (s.hi === L.user || s.lo === L.user));
    if (!s) return null;
    const n = s.games.length;
    const [home, away] = [0, 1, 4].includes(n) ? [s.hi, s.lo] : [s.lo, s.hi];
    return { home, away, label: `${s.rd === 2 ? "Finals" : "Semifinals"} · Game ${n + 1} · Series ${s.hi === L.user ? s.w[0] : s.w[1]}-${s.hi === L.user ? s.w[1] : s.w[0]}` };
  }
  return null;
}
