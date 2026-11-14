// Game theater. Three modes:
//  - replay:  animates a stored event stream (jumbotron, shot chart, lead tracker, PBP, ticking box score)
//  - final:   instant box score
//  - live:    the game is simulated in chunks on the server while YOU coach: timeouts, huddles, subs,
//             strategy, defensive reads, halftime film study and drawn-up final plays (with a shot meter).
import * as U from "./ui.js";
import { S, api, T, ACT, SEG, loadState, hooks } from "./state.js";

const KEYS = ["pts", "fgm", "fga", "tpm", "tpa", "ftm", "fta", "orb", "drb", "ast", "stl", "blk", "tov", "pf"];
let G = null;
let raf = null;

function periodStart(q) { return q <= 4 ? (q - 1) * 720 : 2880 + (q - 5) * 300; }
function clockAt(el, maxQ) {
  let q = 1;
  while (q < maxQ && el >= periodStart(q + 1)) q++;
  const len = q <= 4 ? 720 : 300;
  return { q, rem: Math.max(0, len - (el - periodStart(q))) };
}

function courtSVG() {
  return `<svg class="court-svg" viewBox="0 0 500 470" id="court">
    <defs><linearGradient id="wood" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#14100c"/><stop offset="1" stop-color="#0b0907"/></linearGradient></defs>
    <rect x="0" y="0" width="500" height="470" fill="url(#wood)"/>
    <g fill="none" stroke="rgba(255,255,255,.16)" stroke-width="2">
      <rect x="1" y="1" width="498" height="468"/>
      <rect x="170" y="0" width="160" height="190" fill="color-mix(in srgb, var(--acc) 7%, transparent)"/>
      <circle cx="250" cy="190" r="60"/>
      <path d="M210 52.5 A40 40 0 0 0 290 52.5"/>
      <path d="M30 0 V140 A237.5 237.5 0 0 0 470 140 V0"/>
      <line x1="220" y1="40" x2="280" y2="40" stroke-width="3" stroke="rgba(255,255,255,.4)"/>
      <circle cx="250" cy="52.5" r="7.5" stroke="var(--hot)"/>
      <path d="M190 470 A60 60 0 0 1 310 470"/>
    </g>
    <g id="shots"></g></svg>`;
}

function flowSVG() {
  return `<svg viewBox="0 0 360 100" style="width:100%;height:100px;display:block" id="flow">
    <line x1="0" y1="50" x2="360" y2="50" stroke="rgba(255,255,255,.12)" stroke-dasharray="3 3"/>
    ${[1, 2, 3].map((q) => `<line x1="${q * 90}" y1="0" x2="${q * 90}" y2="100" stroke="rgba(255,255,255,.05)"/>`).join("")}
    <defs><clipPath id="clipT"><rect x="0" y="0" width="360" height="50"/></clipPath><clipPath id="clipB"><rect x="0" y="50" width="360" height="50"/></clipPath></defs>
    <path id="flow-area-h" fill="var(--hc)" opacity=".35" clip-path="url(#clipT)"/><path id="flow-area-a" fill="var(--ac)" opacity=".35" clip-path="url(#clipB)"/>
    <polyline id="flow-line" fill="none" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
}

function boxTable(side) {
  const g = G, tid = side === 0 ? g.doc.h : g.doc.a, t = T(tid);
  const ids = g.order[side];
  const tot = Object.fromEntries(KEYS.map((k) => [k, 0]));
  const rows = ids.map((pid) => {
    const s = g.final ? g.doc.box[pid] : g.stats[pid];
    if (!s) return "";
    KEYS.forEach((k) => (tot[k] += s[k]));
    const min = g.final ? g.doc.box[pid].min : (g.min[pid] || 0) / 60;
    const pm = g.final ? g.doc.box[pid].pm : g.pm[pid] || 0;
    const nm = g.doc.names[pid] || { n: "?" };
    const on = !g.final && g.on[side].has(+pid);
    const sp = g.live && g.snap ? g.snap.players[pid] : null;
    const eBar = sp && on ? `<span class="ebar" title="Energy ${sp.e}"><i style="width:${sp.e}%;background:${sp.e < 60 ? "var(--bad)" : sp.e < 78 ? "var(--warn)" : "var(--good)"}"></i></span>` : "";
    return `<tr class="${g.flashIds.has(+pid) ? "flash" : ""} ${g.live && !on && !g.final && min === 0 ? "dim-row" : ""}"><td class="l nm ${on ? "on-court" : ""}" style="font-size:12px"><span data-player="${pid}" style="cursor:pointer">${U.esc(nm.n)}</span> <span class="mute mono" style="font-size:9px">${nm.pos}</span>${eBar}</td>
      <td>${Math.floor(min)}</td><td class="hl">${s.pts}</td><td>${s.orb + s.drb}</td><td>${s.ast}</td><td>${s.stl}</td><td>${s.blk}</td><td>${s.tov}</td>
      <td>${s.fgm}-${s.fga}</td><td>${s.tpm}-${s.tpa}</td><td>${s.ftm}-${s.fta}</td><td>${s.pf >= 5 ? `<span class="bad">${s.pf}</span>` : s.pf}</td><td class="${pm > 0 ? "good" : pm < 0 ? "bad" : ""}">${U.sign(pm)}</td></tr>`;
  }).join("");
  return `<div class="slab flush box-team" style="--cut:10px"><div class="slab-head" style="padding:12px 14px 0">${U.logo(t, 22)}<h3>${U.esc(t.city)} ${U.esc(t.name)}</h3></div>
    <div class="tbl-wrap"><table class="tbl compact"><thead><tr><th class="l">Player</th><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th><th>STL</th><th>BLK</th><th>TO</th><th>FG</th><th>3P</th><th>FT</th><th>PF</th><th>+/-</th></tr></thead>
    <tbody>${rows}<tr><td class="l mono mute">TEAM</td><td></td><td class="hl">${tot.pts}</td><td>${tot.orb + tot.drb}</td><td>${tot.ast}</td><td>${tot.stl}</td><td>${tot.blk}</td><td>${tot.tov}</td><td>${tot.fgm}-${tot.fga} <span class="mute">${U.pct(tot.fgm, tot.fga)}</span></td><td>${tot.tpm}-${tot.tpa}</td><td>${tot.ftm}-${tot.fta}</td><td>${tot.pf}</td><td></td></tr></tbody></table></div></div>`;
}

function quarterTable() {
  const g = G, d = g.doc;
  const qs = g.final ? d.q : g.qs;
  const ht = T(d.h), at = T(d.a);
  const cols = Math.max(4, qs.length);
  const cell = (i, side) => (qs[i] ? qs[i][side] : "");
  return `<table class="qtable"><tr><th></th>${Array.from({ length: cols }, (_, i) => `<th>${i < 4 ? i + 1 : "OT" + (i - 3)}</th>`).join("")}<th>T</th></tr>
    <tr><td>${at.abbr}</td>${Array.from({ length: cols }, (_, i) => `<td>${cell(i, 1)}</td>`).join("")}<td class="t">${g.score[1]}</td></tr>
    <tr><td>${ht.abbr}</td>${Array.from({ length: cols }, (_, i) => `<td>${cell(i, 0)}</td>`).join("")}<td class="t">${g.score[0]}</td></tr></table>`;
}

function label(doc) {
  if (doc.allstar) return `${doc.s} All-Star Game`;
  if (doc.po) return `${doc.series === "F" ? "The Finals" : "Semifinals"}${doc.gid?.includes("-g") ? " · Game " + doc.gid.split("-g")[1] : ""}`;
  return `${doc.s} regular season · Day ${(doc.day ?? 0) + 1}`;
}

function newSession(doc, opts) {
  G = {
    doc, live: !!opts.live, watch: !!opts.watch, final: !!opts.final, idx: 0, el: 0, speed: 24, paused: false,
    stats: {}, min: {}, pm: {}, on: [new Set(doc.starters[0]), new Set(doc.starters[1])],
    score: [0, 0], qs: [], flow: [[0, 0]], shots: [], flashIds: new Set(), maxQ: 4 + (doc.ot || 0),
    last: performance.now(), endEl: 0, queue: [], modal: null, fetching: false, pending: null, finalPayload: null,
    snap: null, meta: null,
  };
  window.__G = G;
  return G;
}

function initRows(order) {
  G.order = order;
  order.flat().forEach((k) => { G.stats[k] = Object.fromEntries(KEYS.map((x) => [x, 0])); G.min[k] = 0; G.pm[k] = 0; });
}

function shell(doc, controls, extraRight = "") {
  const ht = T(doc.h), at = T(doc.a);
  const rival = doc.rival ? `<span class="chip hot">🔥 ${S.L.consts.tiers[doc.rival]} rivalry</span>` : "";
  return `<div class="theater" style="--hc:${ht.c1};--ac:${at.c1}"><div class="theater-inner">
    <div class="row" style="margin-bottom:14px">
      <button class="btn ghost sm" data-act="game-back">← ${G.live ? "Leave (sims rest)" : "Back"}</button>
      <div class="label" style="margin-left:10px">${U.esc(label(doc))} · ${U.esc(ht.arena || "")}</div>${rival}<div class="sp"></div>
      ${controls}
    </div>
    <div class="jumbo">
      <div class="side" id="side-a">${U.logo(at, 70)}<div><div class="tn">${U.esc(at.name)}</div><div class="rec">${U.esc(at.city)} · AWAY</div><div id="to-a" class="to-pips"></div></div><div class="sp"></div><div class="led" id="sc-a">0</div></div>
      <div class="clockbox"><div class="per" id="per">Q1</div><div class="clk" id="clk">12:00</div><div id="qtab"></div></div>
      <div class="side r" id="side-h">${U.logo(ht, 70)}<div><div class="tn">${U.esc(ht.name)}</div><div class="rec">${U.esc(ht.city)} · HOME</div><div id="to-h" class="to-pips"></div></div><div class="sp"></div><div class="led" id="sc-h">0</div></div>
    </div>
    <div class="theater-grid">
      <div class="col" style="gap:14px">
        ${U.slab("Shot chart", `${courtSVG()}<div class="legend"><span><i style="background:${at.c1}"></i>${at.abbr}</span><span><i style="background:${ht.c1}"></i>${ht.abbr}</span><span>● make  ✕ miss</span></div>`)}
        ${U.slab("Lead tracker", `${flowSVG()}<div class="row"><span class="label" style="color:${ht.c1}">▲ ${ht.abbr}</span><span class="sp"></span><span class="label" style="color:${at.c1}">▼ ${at.abbr}</span></div>`)}
      </div>
      <div id="boxes"></div>
      <div class="pbp-col col" style="gap:14px">${extraRight}${U.slab("Play-by-play", doc.events || G.live ? `<div class="pbp" id="pbp"></div>` : `<div class="empty">Play-by-play is only recorded for your team's games.</div>`)}</div>
    </div>
    <div id="final-bar" style="margin-top:16px"></div>
    <div id="coach-modal"></div>
  </div></div>`;
}

// ============================================================ replay / box score
export async function renderGame(root, gid, watch) {
  cancelAnimationFrame(raf);
  root.innerHTML = `<div class="theater"><div class="loader">LOADING GAME</div></div>`;
  let doc;
  try { doc = await api(`s/${S.sid}/game/${gid}`); } catch (e) { U.toast(e.message, true); location.hash = "#/schedule"; return; }
  const hasEvents = !!(doc.events && doc.events.length);
  newSession(doc, { watch: watch && hasEvents, final: !(watch && hasEvents) });
  const order = [[], []];
  for (const side of [0, 1]) {
    const tid = side === 0 ? doc.h : doc.a;
    const ids = Object.keys(doc.box).filter((k) => doc.box[k].tid === tid);
    ids.sort((a, b) => (doc.box[b].gs - doc.box[a].gs) || (doc.box[b].min - doc.box[a].min));
    order[side] = ids;
  }
  initRows(order);
  G.endEl = hasEvents ? doc.events[doc.events.length - 1].e : 0;
  const controls = G.watch ? `<div class="speed" id="speed"><button class="btn sm" data-act="g-pause" id="g-pause">❚❚</button>
      ${U.seg("g-speed", "24", [["12", "Slow"], ["24", "1×"], ["60", "2.5×"], ["160", "Fast"]])}
      <button class="btn sm hot" data-act="g-skip">Skip to final</button></div>` : "";
  root.innerHTML = shell(doc, controls);
  if (G.final) {
    if (hasEvents) step(Infinity);
    G.final = true;
    G.score = [doc.hs, doc.as];
    paint(true);
    finishUI();
    return;
  }
  G.last = performance.now();
  const loop = (now) => {
    const dt = Math.min(0.25, (now - G.last) / 1000);
    G.last = now;
    if (!G.paused) paint(step(G.el + dt * G.speed));
    if (G.el >= G.endEl && G.idx >= G.doc.events.length) { G.final = true; G.score = [doc.hs, doc.as]; paint(true); finishUI(); return; }
    raf = requestAnimationFrame(loop);
  };
  paint(true);
  raf = requestAnimationFrame(loop);
}

// ============================================================ live coaching
export async function renderLive(root) {
  cancelAnimationFrame(raf);
  // arriving here from browser history (not a Coach live click) must never tip off a new game
  const intent = S.ui.liveIntent;
  S.ui.liveIntent = false;
  if (!intent && !S.L?.derived?.live) { location.replace("#/hub"); return; }
  root.innerHTML = `<div class="theater"><div class="loader">TIPPING OFF</div></div>`;
  let r;
  try { r = await api(`s/${S.sid}/live`, { cmd: "start" }); } catch (e) { U.toast(e.message, true); location.hash = "#/hub"; return; }
  if (r.nogame) {
    await loadState();
    U.toast("Your team doesn't play today. The day was simulated.");
    location.hash = "#/hub";
    return;
  }
  const m = r.meta;
  const doc = { h: m.h, a: m.a, starters: m.starters, names: m.names, box: {}, events: [], q: [], ot: 0, s: S.L.season, day: S.L.day, po: m.po, series: m.series, gid: m.gid, rival: m.rival };
  newSession(doc, { live: true });
  G.meta = m;
  G.side = m.side;
  initRows(m.rosters.map((ids) => ids.map(String)));
  const controls = `<div class="speed" id="speed"><button class="btn sm" data-act="g-pause" id="g-pause">❚❚</button>
      ${U.seg("g-speed", "24", [["12", "Slow"], ["24", "1×"], ["60", "2.5×"], ["160", "Fast"]])}
      <button class="btn sm ghost" data-act="live-simrest">Sim to final</button></div>`;
  root.innerHTML = shell(doc, controls, `<div id="clipboard"></div>`);
  ingest(r);
  if (r.resumed) step(G.endEl);   // jump straight back to where you left off
  paint(true);
  renderClipboard();
  G.last = performance.now();
  raf = requestAnimationFrame(liveLoop);
}

function ingest(r) {
  if (r.events?.length) {
    G.doc.events.push(...r.events);
    G.endEl = G.doc.events[G.doc.events.length - 1].e;
  }
  if (r.snap) {
    G.snap = r.snap;
    G.maxQ = Math.max(4, r.snap.q);
  }
}

function liveLoop(now) {
  if (!G || !G.live) return;
  const dt = Math.min(0.25, (now - G.last) / 1000);
  G.last = now;
  if (!G.paused && !G.modal) {
    const applied = step(G.el + dt * G.speed);
    paint(applied);
    if (applied) renderClipboard();
  }
  // prefetch: ask for the next chunk while ~20 game-seconds are still buffered, so playback never stalls
  // on the network. Paused while a coaching call is queued (it must land at the next dead ball).
  if (!G.fetching && !G.modal && !G.paused && !G.pending && !G.finalPayload && !G.queue.length && G.endEl - G.el < 20) {
    fetchChunk();
  }
  const drained = G.idx >= G.doc.events.length && G.el >= G.endEl;
  if (drained && !G.fetching && !G.modal && !G.paused) {
    if (G.queue.length) runQueue();
    else if (G.pending) { const d = G.pending; G.pending = null; showDecision(d); }
    else if (G.finalPayload) { liveFinal(G.finalPayload); return; }
    else fetchChunk();
  }
  raf = requestAnimationFrame(liveLoop);
}

async function liveCmd(body) {
  const r = await api(`s/${S.sid}/live`, body);
  ingest(r);
  return r;
}

async function fetchChunk() {
  G.fetching = true;
  try {
    const r = await liveCmd({ cmd: "step" });
    if (r.final) G.finalPayload = r;
    else if (r.decision) G.pending = r.decision;
  } catch (e) {
    U.toast(e.message, true);
    G.paused = true;
  } finally {
    G.fetching = false;
  }
}

async function runQueue() {
  const job = G.queue.shift();
  G.fetching = true;
  try { await job(); } catch (e) { U.toast(e.message, true); } finally { G.fetching = false; renderClipboard(); }
}

// ------------------------------------------------------------ clipboard (coach panel)
const LIVE_STRAT = [["pace", [["slow", "Slow"], ["normal", "Norm"], ["fast", "Fast"]]], ["focus", [["inside", "In"], ["balanced", "Bal"], ["perimeter", "Out"]]],
  ["defense", [["conservative", "Contain"], ["normal", "Norm"], ["aggressive", "Gamble"]]], ["star", [["share", "Share"], ["normal", "Norm"], ["heliocentric", "Star"]]]];

function renderClipboard() {
  const el = document.getElementById("clipboard");
  if (!el || !G?.snap) return;
  const side = G.side, sn = G.snap, names = G.doc.names;
  const to = sn.timeouts[side];
  const mo = sn.mo[side] - sn.mo[1 - side];
  const strat = sn.strat[side];
  const onIds = [...G.on[side]];
  const bench = G.order[side].filter((id) => !G.on[side].has(+id));
  const sel = G.subOut;
  const prow = (id, onCourt) => {
    const p = sn.players[id] || { e: 100, f: 0 };
    const n = names[id] || { n: "?" };
    const out = p.inj || p.f >= 6;
    return `<div class="cb-p ${String(sel) === String(id) ? "sel" : ""} ${out ? "out" : ""}" data-act="${onCourt ? "cb-out" : "cb-in"}" data-pid="${id}">
      <span class="pos" style="min-width:24px">${n.pos}</span><span class="nm">${U.esc(n.n)}</span>${p.hold && onCourt ? `<span class="chip acc" title="Coach-locked on the floor">🔒</span>` : ""}
      <span class="sp"></span>${p.f ? `<span class="mono ${p.f >= 5 ? "bad" : p.f >= 3 ? "warn" : "mute"}" style="font-size:10px">${p.f}PF</span>` : ""}
      <span class="ebar wide"><i style="width:${p.e}%;background:${p.e < 60 ? "var(--bad)" : p.e < 78 ? "var(--warn)" : "var(--good)"}"></i></span></div>`;
  };
  const html = U.slab("Coach's clipboard", `
    <div class="row" style="margin-bottom:10px"><button class="btn sm ${to ? "pri" : ""}" data-act="live-timeout" ${to && !G.queue.length ? "" : "disabled"}>⏸ Timeout · ${to}</button><span class="sp"></span>
      <div style="text-align:right"><div class="label">Momentum</div><div class="momo"><i style="left:${50 + mo * 50}%"></i></div></div></div>
    <div class="cb-strat">${LIVE_STRAT.map(([k, opts]) => `<div class="row"><span class="label" style="width:58px">${k}</span>${U.seg(`live-${k}`, strat[k], opts)}</div>`).join("")}</div>
    <div class="label" style="margin:12px 0 6px">On the floor ${sel ? `<span class="acc">· pick a sub ↓</span>` : `<span class="mute">· click to sub out</span>`}</div>
    ${onIds.map((id) => prow(id, true)).join("")}
    <div class="label" style="margin:10px 0 6px">Bench</div>
    <div style="max-height:180px;overflow:auto">${bench.map((id) => prow(id, false)).join("")}</div>
    ${G.queue.length ? `<div class="label acc" style="margin-top:8px">Call queued for the next dead ball…</div>` : ""}`);
  if (html !== G.clipHTML) {   // only touch the DOM when something changed, so clicks never get eaten
    G.clipHTML = html;
    el.innerHTML = html;
  }
}

for (const [k] of LIVE_STRAT) {
  SEG[`live-${k}`] = (v) => {
    if (!G?.live) return;
    G.snap.strat[G.side][k] = v;
    G.queue.push(() => liveCmd({ cmd: "strategy", k, v }));
    renderClipboard();
  };
}
ACT["cb-out"] = (el) => { if (!G?.live) return; G.subOut = G.subOut === el.dataset.pid ? null : el.dataset.pid; renderClipboard(); };
ACT["cb-in"] = (el) => {
  if (!G?.live || !G.subOut) { U.toast("First click the player coming OUT."); return; }
  const out = +G.subOut, inn = +el.dataset.pid;
  G.subOut = null;
  G.queue.push(() => liveCmd({ cmd: "sub", out, in: inn }));
  renderClipboard();
};
ACT["live-timeout"] = () => {
  if (!G?.live) return;
  G.queue.push(async () => { const r = await liveCmd({ cmd: "timeout" }); showHuddle(r.huddle, r.read); });
  renderClipboard();
};
ACT["live-simrest"] = async () => {
  if (!G?.live || !confirm("Let your assistants finish the game?")) return;
  cancelAnimationFrame(raf);
  const r = await api(`s/${S.sid}/live`, { cmd: "sim_rest" });
  await finishToBox(r.gid);
};

// ------------------------------------------------------------ decision modals
function modalHTML(title, body, cls = "") {
  return `<div class="coach-bg"><div class="coach-card ${cls}"><div class="kicker">${title}</div>${body}</div></div>`;
}
function openModal(html) { G.modal = true; document.getElementById("coach-modal").innerHTML = html; }
function closeModal() { G.modal = null; const m = document.getElementById("coach-modal"); if (m) m.innerHTML = ""; G.last = performance.now(); renderClipboard(); }
ACT["coach-continue"] = () => closeModal();

function resultHTML(res, next = "Back to the game") {
  return `<div class="coach-result ${res.ok ? "good" : "bad"}"><div class="big">${res.ok ? "✓ SUCCESS" : "✕ BACKFIRED"}</div><p>${U.esc(res.txt)}</p></div>
    <button class="btn pri lg" style="width:100%" data-act="coach-continue">${next}</button>`;
}

function scoreline() {
  const s = G.snap, side = G.side, m = s.score[side] - s.score[1 - side];
  return `${m > 0 ? "Up " + m : m < 0 ? "Down " + -m : "Tied"} · ${U.qLabel(s.q)} ${U.clockStr(s.clock)}`;
}

function showDecision(d) {
  if (d.type === "break") {
    if (d.halftime) return showHalftime(d.halftime);
    openModal(modalHTML(`End of ${U.qLabel(d.q)}`, `<h2 style="margin:6px 0 10px">${scoreline()}</h2>
      <p class="dim">Use the clipboard to change your lineup or strategy before the next quarter starts.</p>
      <button class="btn pri lg" style="width:100%" data-act="coach-continue">Start ${U.qLabel(d.q + 1)} →</button>`));
    return;
  }
  if (d.type === "run") {
    const opp = T(G.side === 0 ? G.doc.a : G.doc.h);
    const to = G.snap.timeouts[G.side];
    G.read = d.read;
    openModal(modalHTML("Momentum alert", `<h2 style="margin:6px 0 6px">${U.esc(opp.name)} are on a ${d.run}-0 run</h2>
      <p class="dim">${scoreline()}. Stop the bleeding, or let your guys play through it.</p>
      <div class="col" style="gap:8px;margin-top:14px">
        <button class="btn pri lg" data-act="dec-timeout" ${to ? "" : "disabled"}>⏸ Call timeout (${to} left)</button>
        <button class="btn lg" data-act="dec-read">🎯 Adjust coverage on ${U.esc(d.read.name)}</button>
        <button class="btn ghost" data-act="coach-continue">Ride it out</button></div>`));
    return;
  }
  if (d.type === "final_play") return showFinalPlay(d);
  closeModal();
}

ACT["dec-timeout"] = async () => {
  try { const r = await liveCmd({ cmd: "timeout" }); showHuddle(r.huddle, r.read); } catch (e) { U.toast(e.message, true); closeModal(); }
};
ACT["dec-read"] = () => showRead(G.read);

function showHuddle(h, read) {
  G.read = read || G.read;
  openModal(modalHTML("Timeout huddle", `<h2 style="margin:6px 0 8px">What do they need to hear?</h2>
    <div class="grid g4" style="gap:8px;margin-bottom:14px">
      <div class="stat-tile"><div class="label">Score</div><div class="v" style="font-size:16px">${h.margin > 0 ? "+" + h.margin : h.margin}</div></div>
      <div class="stat-tile"><div class="label">Floor energy</div><div class="v" style="font-size:16px">${h.energy}</div></div>
      <div class="stat-tile"><div class="label">Their run</div><div class="v" style="font-size:16px">${h.run}-0</div></div>
      <div class="stat-tile"><div class="label">Our TOs</div><div class="v" style="font-size:16px">${h.tov}</div></div>
      <div class="stat-tile"><div class="label">Their energy</div><div class="v" style="font-size:16px">${h.opp_energy ?? "—"}</div></div>
      <div class="stat-tile"><div class="label">Their off. boards</div><div class="v" style="font-size:16px">${h.opp_oreb ?? "—"}</div></div>
      <div class="stat-tile" style="grid-column:span 2"><div class="label">Our hot hand</div><div class="v" style="font-size:14px">${h.hot ? `${U.esc(h.hot.name)} · ${h.hot.pts} pts (${h.hot.fgm}/${h.hot.fga})` : "—"}</div></div></div>
    <p class="dim" style="margin-top:0">Read the room. The right message gives a boost; the wrong one costs you.</p>
    <div class="col" style="gap:8px">${(h.options || []).map((o) => `<button class="btn lg" data-act="huddle" data-c="${o.key}">${U.esc(o.label)}</button>`).join("")}</div>`));
}
ACT["huddle"] = async (el) => {
  try {
    const r = await liveCmd({ cmd: "huddle", choice: el.dataset.c });
    const readBtn = G.read ? `<button class="btn lg" style="width:100%;margin-bottom:8px" data-act="dec-read">🎯 Also adjust coverage on ${U.esc(G.read.name)}</button>` : "";
    openModal(modalHTML("Huddle result", `<div class="coach-result ${r.result.ok ? "good" : "bad"}"><div class="big">${r.result.ok ? "✓ SUCCESS" : "✕ BACKFIRED"}</div><p>${U.esc(r.result.txt)}</p></div>${readBtn}<button class="btn pri lg" style="width:100%" data-act="coach-continue">Back to the game</button>`));
  } catch (e) { U.toast(e.message, true); closeModal(); }
};

function showRead(rd) {
  if (!rd) return closeModal();
  const z = rd.zones;
  const zl = [["three", "3PT"], ["mid", "MID"], ["rim", "RIM"], ["post", "POST"]].map(([k, l]) => `<div class="stat-tile"><div class="label">${l}</div><div class="v" style="font-size:18px">${z[k][0]}/${z[k][1]}</div></div>`).join("");
  openModal(modalHTML("Defensive read", `<h2 style="margin:6px 0 4px">${U.esc(rd.name)} has ${rd.pts} points</h2>
    <p class="dim" style="margin-top:0">Here's his shot chart tonight. Take away what's hurting you. The wrong coverage opens him up even more. (One adjustment per quarter.)</p>
    <div class="grid g4" style="gap:8px;margin-bottom:14px">${zl}</div>
    <div class="col" style="gap:8px">
      <button class="btn lg" data-act="read" data-c="three">Chase him off the three-point line</button>
      <button class="btn lg" data-act="read" data-c="paint">Wall off the paint (rim + post)</button>
      <button class="btn lg" data-act="read" data-c="mid">Top-lock his mid-range pull-ups</button></div>`));
}
ACT["read"] = async (el) => {
  try {
    const r = await liveCmd({ cmd: "def_read", pid: G.read.pid, choice: el.dataset.c });
    G.read = null;
    openModal(modalHTML("Coverage result", resultHTML(r.result)));
  } catch (e) { U.toast(e.message, true); closeModal(); }
};

function showHalftime(h) {
  if (h.kind === "film") return showFilm(h);
  if (h.kind === "matchup") {
    const z = h.star.zones;
    const zl = [["three", "3PT"], ["mid", "MID"], ["rim", "RIM"], ["post", "POST"]].map(([k, l]) => `<div class="stat-tile"><div class="label">${l}</div><div class="v" style="font-size:16px">${z[k][0]}/${z[k][1]}</div></div>`).join("");
    openModal(modalHTML("Halftime · defensive assignment", `<h2 style="margin:6px 0 4px">Who guards ${U.esc(h.star.name)}?</h2>
      <p class="dim" style="margin-top:0">${U.esc(h.star.name)} has ${h.star.pts} points. Look at where he's scoring, then pick the right kind of defender: a perimeter stopper or a paint protector.</p>
      <div class="grid g4" style="gap:8px;margin-bottom:12px">${zl}</div>
      <div class="col" style="gap:8px">${h.options.map((o) => `<button class="film-z" data-act="half" data-c="${o.pid}"><div class="row"><b>${U.esc(o.name)}</b><span class="pos">${o.pos}</span><span class="sp"></span><span class="mono dim">Perimeter D ${o.perd} · Interior D ${o.intd}</span></div></button>`).join("")}</div>`, "wide"));
    return;
  }
  if (h.kind === "mismatch") {
    openModal(modalHTML("Halftime · hunt the mismatch", `<h2 style="margin:6px 0 4px">Where do we attack?</h2>
      <p class="dim" style="margin-top:0">Compare each scorer's best skill with his defender's matching rating: inside scoring against Interior D, outside shooting against Perimeter D. Feed the biggest edge all half.</p>
      <div class="col" style="gap:8px">${h.options.map((o) => `<button class="film-z" data-act="half" data-c="${o.pid}"><div class="row"><b>${U.esc(o.name)}</b><span class="pos">${o.pos}</span><span class="sp"></span><span class="mono dim">Inside ${o.inside} · Outside ${o.outside}</span></div>
        <div class="row" style="margin-top:4px"><span class="label">guarded by ${U.esc(o.vs)}</span><span class="sp"></span><span class="mono dim">Perimeter D ${o.vs_perd} · Interior D ${o.vs_intd}</span></div></button>`).join("")}</div>`, "wide"));
    return;
  }
  openModal(modalHTML("Halftime · second-half tempo", `<h2 style="margin:6px 0 4px">${scoreline()}</h2>
    <p class="dim" style="margin-top:0">Set the second-half pace. Fresher legs and a deeper bench favor running; a lead (or sloppy ball-handling) favors slowing it down.</p>
    <div class="grid g4" style="gap:8px;margin-bottom:12px">
      <div class="stat-tile"><div class="label">Bench quality</div><div class="v" style="font-size:15px">${h.our_bench} <span class="mute">vs ${h.their_bench}</span></div></div>
      <div class="stat-tile"><div class="label">Bench energy</div><div class="v" style="font-size:15px">${h.our_energy} <span class="mute">vs ${h.their_energy}</span></div></div>
      <div class="stat-tile"><div class="label">Margin</div><div class="v" style="font-size:15px">${h.margin > 0 ? "+" : ""}${h.margin}</div></div>
      <div class="stat-tile"><div class="label">Our turnovers</div><div class="v" style="font-size:15px">${h.our_tov}</div></div></div>
    <div class="grid g3" style="gap:8px">${[["slow", "🐢 Slow it down"], ["normal", "⚖️ Stay the course"], ["fast", "⚡ Push the pace"]].map(([k, l]) => `<button class="film-z" data-act="half" data-c="${k}"><div class="v" style="font-size:15px">${l}</div></button>`).join("")}</div>`, "wide"));
}
ACT["half"] = async (el) => {
  try {
    const r = await liveCmd({ cmd: "half", choice: el.dataset.c });
    openModal(modalHTML("Halftime adjustment", resultHTML(r.result, "Start the second half →")));
  } catch (e) { U.toast(e.message, true); closeModal(); }
};

function showFilm(f) {
  const z = f.zones;
  const zl = [["three", "3PT"], ["mid", "Mid-range"], ["rim", "At the rim"], ["post", "Post-ups"]].map(([k, l]) => `<button class="film-z" data-act="half" data-c="${k}"><div class="label">${l}</div><div class="v">${z[k]?.pts ?? 0} pts</div><div class="mono dim" style="font-size:11px">${z[k]?.fgm ?? 0}/${z[k]?.fga ?? 0} FG</div></button>`).join("");
  openModal(modalHTML("Halftime film session", `<h2 style="margin:6px 0 4px">${scoreline()}</h2>
    <p class="dim" style="margin-top:0">Here's how they scored in the first half. Pick the zone your defense will sell out to take away in the second half. Guess right and it dries up; guess wrong and they'll find it even easier.</p>
    <div class="grid g4" style="gap:8px">${zl}</div>`, "wide"));
}


const CALLS = [["iso", "Isolation", "Clear out for your best player"], ["three", "Pick-and-pop for three", "Your best shooter, open look from deep"], ["pnr", "Pick-and-roll to the rim", "Your best finisher attacks the basket"], ["post", "Post entry", "Feed your best post scorer"]];
function showFinalPlay(d) {
  const m = d.margin;
  openModal(modalHTML("Draw up the final play", `<h2 style="margin:6px 0 4px">${U.clockStr(d.clock)} left · ${m > 0 ? "up " + m : m < 0 ? "down " + -m : "tied"} · your ball</h2>
    <p class="dim" style="margin-top:0">Pick the play, then nail the timing on the shot meter. A perfect release gives a big boost; a bad one probably misses.</p>
    <div class="grid g2" style="gap:8px">${CALLS.map(([k, l, s]) => `<button class="film-z" data-act="fp-call" data-c="${k}"><div class="v" style="font-size:15px">${l}</div><div class="dim" style="font-size:12px">${s}</div></button>`).join("")}</div>`, "wide"));
}
ACT["fp-call"] = (el) => {
  const call = el.dataset.c;
  openModal(modalHTML("Execute!", `<h2 style="margin:6px 0 10px">Click when the needle hits the green</h2><div id="meter-host"></div>`));
  const coach = S.L.teams[S.L.user].upg?.coaching || 0;
  U.shotMeter(document.getElementById("meter-host"), coach, async (acc, grade) => {
    try {
      const r = await liveCmd({ cmd: "final_play", call, acc });
      const g = r.result.grade;
      openModal(modalHTML("Release", `<div class="coach-result ${g === "perfect" || g === "good" ? "good" : g === "ok" ? "" : "bad"}"><div class="big">${g.toUpperCase()} RELEASE</div><p>${g === "perfect" ? "Pure. That's as good a look as you'll get." : g === "good" ? "Good timing. Strong look." : g === "ok" ? "Average release. Coin-flip territory." : "Rushed it. That's going to be tough."}</p></div>
        <button class="btn pri lg" style="width:100%" data-act="coach-continue">Run the play →</button>`));
    } catch (e) { U.toast(e.message, true); closeModal(); }
  });
};

async function liveFinal(r) {
  cancelAnimationFrame(raf);
  step(Infinity);
  paint(true);
  const ch = r.challenges || [];
  const ok = ch.filter((c) => c.ok).length;
  const won = G.snap.score[G.side] > G.snap.score[1 - G.side];
  openModal(modalHTML("Final", `<h2 style="margin:6px 0 4px">${won ? "WIN" : "LOSS"} · ${G.snap.score[1]}–${G.snap.score[0]}</h2>
    <p class="dim">Coaching calls: <b class="${ok ? "good" : ""}">${ok}/${ch.length}</b> won${ok ? ` (+${Math.min(3, ok)} franchise points)` : ""}.</p>
    <div class="col" style="gap:8px;margin-top:12px"><button class="btn pri lg" data-act="live-box" data-gid="${r.gid}">Final box score →</button><button class="btn ghost" data-act="live-hub">Back to hub</button></div>`));
}
ACT["live-box"] = (el) => finishToBox(el.dataset.gid);
// leaving a finished live game replaces the #/live history entry, so Back goes to the hub, never a new game
ACT["live-hub"] = async () => { G = null; await loadState(); location.replace("#/hub"); };
async function finishToBox(gid) {
  G = null;
  await loadState();
  location.replace(`#/game/${gid}`);
}

// ============================================================ shared animation
function addMinutes(dt) {
  if (dt <= 0) return;
  for (const side of [0, 1]) for (const pid of G.on[side]) G.min[pid] = (G.min[pid] || 0) + dt;
}

function step(target) {
  const ev = G.doc.events || [];
  let applied = false;
  G.flashIds = new Set();
  const pbpRows = [];
  while (G.idx < ev.length && ev[G.idx].e <= target) {
    const e = ev[G.idx++];
    addMinutes(e.e - G.el);
    G.el = e.e;
    applied = true;
    if (e.d) for (const [pid, k, n] of e.d) { if (G.stats[pid]) G.stats[pid][k] += n; G.flashIds.add(pid); }
    if (e.k === "sub") { G.on[e.tm].delete(e.out); G.on[e.tm].add(e.in); }
    const dh = e.s[0] - G.score[0], da = e.s[1] - G.score[1];
    if (dh || da) {
      for (const pid of G.on[0]) G.pm[pid] = (G.pm[pid] || 0) + dh - da;
      for (const pid of G.on[1]) G.pm[pid] = (G.pm[pid] || 0) + da - dh;
      G.score = [...e.s];
      G.flow.push([e.e, e.s[0] - e.s[1]]);
    }
    if (e.k === "endq") {
      const prev = G.qs.reduce((a, q) => [a[0] + q[0], a[1] + q[1]], [0, 0]);
      G.qs.push([e.s[0] - prev[0], e.s[1] - prev[1]]);
      G.maxQ = Math.max(G.maxQ, e.q + (e.q >= 4 && e.s[0] === e.s[1] ? 1 : 0));
    }
    if (e.k === "q") G.maxQ = Math.max(G.maxQ, e.q);
    if (e.sh) G.shots.push({ ...e.sh, tm: e.tm });
    pbpRows.push(e);
  }
  if (target !== Infinity) { addMinutes(Math.min(target, G.endEl) - G.el); G.el = Math.min(target, G.endEl); }
  if (pbpRows.length) appendPbp(pbpRows);
  return applied;
}

function appendPbp(rows) {
  const box = document.getElementById("pbp");
  if (!box) return;
  const ht = T(G.doc.h), at = T(G.doc.a);
  const html = rows.map((e) => {
    const col = ["q", "endq", "start"].includes(e.k) ? "transparent" : e.k === "coach" ? "var(--volt)" : e.tm === 0 ? ht.c1 : at.c1;
    return `<div class="pbp-row ${e.k}"><span class="t">${["endq", "q"].includes(e.k) ? "" : U.qLabel(e.q) + " " + U.clockStr(e.c)}</span><span class="bar2" style="background:${col}"></span><span class="txt">${U.esc(e.txt)}</span><span class="sc">${e.k === "make" || e.k === "ft" ? `${e.s[1]}-${e.s[0]}` : ""}</span></div>`;
  }).reverse().join("");
  box.insertAdjacentHTML("afterbegin", html);
  while (box.children.length > 400) box.lastElementChild.remove();
}

function paint(full) {
  const g = G;
  if (!g) return;
  const ht = T(g.doc.h), at = T(g.doc.a);
  const c = g.final ? { q: g.maxQ, rem: 0 } : clockAt(g.el, g.maxQ);
  const set = (id, v) => { const el = document.getElementById(id); if (el && el.innerHTML !== String(v)) el.innerHTML = v; };
  set("sc-h", g.score[0]);
  set("sc-a", g.score[1]);
  set("per", g.final ? `<span class="final-stamp">FINAL${g.doc.ot ? (g.doc.ot > 1 ? ` / ${g.doc.ot}OT` : " / OT") : ""}</span>` : U.qLabel(c.q));
  set("clk", g.final ? "0.0" : U.clockStr(c.rem));
  if (g.live && g.snap) {
    const pips = (n) => "●".repeat(n) || "—";
    set("to-h", `<span class="label">TO ${pips(g.snap.timeouts[0])}</span>`);
    set("to-a", `<span class="label">TO ${pips(g.snap.timeouts[1])}</span>`);
  }
  document.getElementById("side-h")?.classList.toggle("lead", g.score[0] > g.score[1]);
  document.getElementById("side-a")?.classList.toggle("lead", g.score[1] > g.score[0]);
  if (!full) return;
  set("qtab", quarterTable());
  const boxes = document.getElementById("boxes");
  if (boxes) boxes.innerHTML = boxTable(1) + boxTable(0);
  const sg = document.getElementById("shots");
  if (sg && sg.childElementCount !== g.shots.length) {
    const html = g.shots.slice(sg.childElementCount).map((s) => {
      const col = s.tm === 0 ? ht.c1 : at.c1;
      const x = 250 + s.x * 10, y = 52.5 + s.y * 10;
      return s.m ? `<circle class="shot-dot" cx="${x}" cy="${y}" r="6" fill="${col}" stroke="#000" stroke-width="1"/>`
        : `<g class="shot-dot" stroke="${col}" stroke-width="2.2" opacity=".75"><line x1="${x - 4.5}" y1="${y - 4.5}" x2="${x + 4.5}" y2="${y + 4.5}"/><line x1="${x + 4.5}" y1="${y - 4.5}" x2="${x - 4.5}" y2="${y + 4.5}"/></g>`;
    }).join("");
    sg.insertAdjacentHTML("beforeend", html);
  }
  const total = Math.max(2880, periodStart(g.maxQ + 1));
  const pts = g.flow.concat(g.final ? [] : [[g.el, g.score[0] - g.score[1]]]);
  const mx = Math.max(10, ...pts.map((p) => Math.abs(p[1])));
  const P = pts.map(([e, m]) => [(e / total) * 360, 50 - (m / mx) * 46]);
  const line = document.getElementById("flow-line");
  if (line) {
    line.setAttribute("points", P.map((p) => p.join(",")).join(" "));
    const lastX = P.length ? P[P.length - 1][0] : 0;
    const area = `M0,50 ${P.map((p) => `L${p[0]},${p[1]}`).join(" ")} L${lastX},50 Z`;
    document.getElementById("flow-area-h").setAttribute("d", area);
    document.getElementById("flow-area-a").setAttribute("d", area);
  }
}

function finishUI() {
  const d = G.doc;
  const won = d.hs > d.as ? d.h : d.a;
  const pog = d.pog && d.names[d.pog];
  const fb = document.getElementById("final-bar");
  const speed = document.getElementById("speed");
  if (speed) speed.innerHTML = `<span class="final-stamp">FINAL</span>`;
  const ch = d.challenges || [];
  if (fb) fb.innerHTML = U.slab("", `<div class="row wrap" style="gap:16px">${U.logo(T(won), 46)}<div><div class="display" style="font-size:20px;font-weight:800">${U.esc(T(won).city)} ${U.esc(T(won).name)} win ${Math.max(d.hs, d.as)}–${Math.min(d.hs, d.as)}${d.ot ? " in OT" : ""}</div>
    ${pog ? `<div class="dim" style="margin-top:4px">Player of the game: <b data-player="${d.pog}" style="cursor:pointer;color:var(--txt)">${U.esc(pog.fn)}</b> — ${d.box[d.pog].pts} pts, ${d.box[d.pog].orb + d.box[d.pog].drb} reb, ${d.box[d.pog].ast} ast</div>` : ""}
    ${ch.length ? `<div class="dim" style="margin-top:4px">Coaching calls won: <b>${ch.filter((c) => c.ok).length}/${ch.length}</b></div>` : ""}</div>
    <div class="sp"></div><button class="btn pri lg" data-act="game-back">Continue →</button></div>`, { cls: "glow" });
}

ACT["game-back"] = async () => {
  if (G?.live) {
    if (!confirm("Leave now? Your assistants will finish the game.")) return;
    cancelAnimationFrame(raf);
    try { await api(`s/${S.sid}/live`, { cmd: "sim_rest" }); } catch (e) { /* already finished */ }
    G = null;
    await loadState();
    location.replace("#/hub");
    return;
  }
  cancelAnimationFrame(raf);
  G = null;
  if (history.length > 1 && !location.hash.includes("watch=1")) history.back(); else location.hash = "#/hub";
};
ACT["g-pause"] = (el) => { if (!G) return; G.paused = !G.paused; el.textContent = G.paused ? "▶" : "❚❚"; G.last = performance.now(); };
ACT["g-skip"] = () => {
  if (!G) return;
  step(Infinity);
  G.final = true;
  G.score = [G.doc.hs, G.doc.as];
  paint(true);
  finishUI();
  cancelAnimationFrame(raf);
};
SEG["g-speed"] = (v, btn) => {
  if (!G) return;
  G.speed = +v;
  btn.parentElement.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b === btn));
};
