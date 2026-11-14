// Shared UI atoms: escaping, formatting, team logos, stars, avatars, player links.
export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
export const money = (m) => `$${(+m || 0).toFixed(1)}M`;
export const pct = (a, b) => (b ? (a / b).toFixed(3).replace(/^0/, "") : "—");
export const f1 = (n) => (Number.isFinite(n) ? n.toFixed(1) : "—");
export const sign = (n) => (n > 0 ? `+${n}` : `${n}`);
export const ht = (inches) => `${Math.floor(inches / 12)}'${inches % 12}"`;
export const clockStr = (secs) => {
  secs = Math.max(0, secs);
  if (secs < 60) return secs.toFixed(1);
  const m = Math.floor(secs / 60), s = Math.floor(secs % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
};
export const qLabel = (q) => (q <= 4 ? `Q${q}` : `OT${q - 4}`);

const GLYPHS = {
  bolt: `<path d="M57 14 L29 54 H46 L39 86 L71 42 H54 L62 14 Z"/>`,
  flame: `<path d="M50 14 C59 29 71 38 69 57 C68 72 59 82 50 82 C39 82 31 73 31 61 C31 50 37 44 42 37 C42 46 46 51 51 53 C46 41 47 27 50 14 Z"/>`,
  peak: `<path d="M14 76 L39 34 L48 48 L59 28 L86 76 Z"/><path d="M59 28 L66 40 L61 38 L56 43 L53 38 Z" fill="#fff" opacity=".85"/>`,
  trident: `<path d="M47 84 V46 H38 L33 22 L40 29 V39 H47 V20 L50 12 L53 20 V39 H60 V29 L67 22 L62 46 H53 V84 Z"/>`,
  crown: `<path d="M20 68 L24 32 L38 49 L50 26 L62 49 L76 32 L80 68 Z"/><rect x="20" y="72" width="60" height="8"/>`,
  raven: `<path d="M12 38 L50 56 L88 38 L74 62 L50 74 L26 62 Z"/><path d="M43 30 L50 20 L57 30 L50 50 Z"/>`,
  anvil: `<path d="M20 32 H80 V40 C70 42 64 47 62 54 H67 V63 H33 V54 H38 C36 47 30 42 20 40 Z"/><rect x="28" y="68" width="44" height="9"/>`,
  wave: `<path d="M14 56 C25 36 41 36 50 52 C57 64 71 64 86 42" fill="none" stroke="currentColor" stroke-width="9" stroke-linecap="round"/><path d="M14 74 C25 58 41 58 50 70 C57 79 71 79 86 64" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" opacity=".6"/>`,
  comet: `<circle cx="62" cy="38" r="14"/><path d="M53 48 L16 84 L28 63 L14 68 L45 36 Z" opacity=".75"/>`,
  fang: `<path d="M32 22 C32 48 38 64 44 80 C47 62 47 44 47 22 Z"/><path d="M68 22 C68 48 62 64 56 80 C53 62 53 44 53 22 Z"/>`,
  pickaxe: `<path d="M18 36 C34 20 66 20 82 36 C66 30 34 30 18 36 Z"/><rect x="46" y="28" width="8" height="54" rx="2"/>`,
  axe: `<rect x="47" y="16" width="7" height="68" rx="2"/><path d="M54 22 C72 22 82 34 82 48 C72 44 62 44 54 46 Z"/>`,
  owl: `<path d="M22 30 L34 40 L50 34 L66 40 L78 30 L74 62 C70 76 60 82 50 82 C40 82 30 76 26 62 Z"/><circle cx="39" cy="52" r="8" fill="#000"/><circle cx="61" cy="52" r="8" fill="#000"/><path d="M46 62 L50 70 L54 62 Z" fill="#000"/>`,
  swirl: `<path d="M50 18 C72 18 84 34 80 52 C76 68 58 74 48 66 C40 60 42 48 50 46 C58 44 60 54 54 56" fill="none" stroke="currentColor" stroke-width="8" stroke-linecap="round"/><path d="M26 70 L40 62 M20 54 L34 50" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>`,
  tree: `<path d="M50 12 L72 42 H62 L78 62 H58 V84 H42 V62 H22 L38 42 H28 Z"/>`,
  stinger: `<path d="M30 80 C30 56 40 46 54 44 C66 42 72 34 70 24 L80 30 C82 44 72 54 58 56 C46 58 42 66 44 80 Z"/><path d="M70 24 L76 12 L82 28 Z"/>`,
  tusk: `<path d="M26 26 C26 58 40 76 66 76 C52 70 40 58 38 26 Z"/><path d="M74 26 C74 48 70 58 62 64 C64 52 62 40 62 26 Z" opacity=".6"/>`,
  jaw: `<path d="M14 40 L86 34 L80 44 L70 40 L62 48 L54 42 L46 50 L38 44 L30 52 L22 44 Z"/><path d="M18 62 L82 66 L76 56 L68 60 L60 52 L52 58 L44 50 L36 58 L28 50 Z"/>`,
  star: `<path d="M50 12 L60 38 L88 40 L66 58 L74 86 L50 70 L26 86 L34 58 L12 40 L40 38 Z"/>`,
  fox: `<path d="M18 18 L40 38 L50 34 L60 38 L82 18 L76 52 L50 82 L24 52 Z"/><path d="M36 56 L46 60 L40 50 Z M64 56 L54 60 L60 50 Z" fill="#000"/>`,
};
const SHAPES = {
  hex: (a) => `<polygon points="50,3 93,27 93,73 50,97 7,73 7,27" ${a}/>`,
  shield: (a) => `<path d="M50 3 L91 15 V50 C91 75 73 89 50 97 C27 89 9 75 9 50 V15 Z" ${a}/>`,
  circle: (a) => `<circle cx="50" cy="50" r="46" ${a}/>`,
  diamond: (a) => `<polygon points="50,2 98,50 50,98 2,50" ${a}/>`,
};
let gid = 0;
export function logo(t, size = 36) {
  if (!t) return "";
  const id = `lg${++gid}`;
  return `<svg class="logo" width="${size}" height="${size}" viewBox="0 0 100 100" aria-label="${esc(t.name)}">
    <defs><linearGradient id="${id}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${t.c2}"/><stop offset="1" stop-color="#050608"/></linearGradient></defs>
    ${SHAPES[t.shape]?.(`fill="url(#${id})" stroke="${t.c1}" stroke-width="3.5"`) || ""}
    <g fill="${t.c1}" color="${t.c1}" transform="translate(50 50) scale(.78) translate(-50 -50)">${GLYPHS[t.glyph] || ""}</g></svg>`;
}

const STAR = "M12 2l2.9 6.6 7.1.6-5.4 4.7 1.6 7-6.2-3.8-6.2 3.8 1.6-7L2 9.2l7.1-.6z";
let starId = 0;
// 1-5 stars in half-star steps
export function stars(n, cls = "") {
  n = Math.max(0, Math.min(5, Math.round((+n || 0) * 2) / 2));
  let s = `<span class="stars ${cls}" title="${n} star${n === 1 ? "" : "s"}">`;
  for (let i = 1; i <= 5; i++) {
    if (n >= i) s += `<svg viewBox="0 0 24 24"><path class="on" d="${STAR}"/></svg>`;
    else if (n >= i - 0.5) {
      const id = `hs${++starId}`;
      s += `<svg viewBox="0 0 24 24"><defs><clipPath id="${id}"><rect x="0" y="0" width="12" height="24"/></clipPath></defs><path class="off" d="${STAR}"/><path class="on" d="${STAR}" clip-path="url(#${id})"/></svg>`;
    } else s += `<svg viewBox="0 0 24 24"><path class="off" d="${STAR}"/></svg>`;
  }
  return s + "</span>";
}
const fmtStar = (n) => `${n}★`;
// a player's rating: stars only (scouted prospects show a star range)
export const ovrBadge = (p, lg = false) => (p.fog && p.scout
  ? `<span class="srange ${lg ? "lg" : ""}" title="Scouted rating range">${p.scout.ovr[0] === p.scout.ovr[1] ? fmtStar(p.scout.ovr[0]) : `${fmtStar(p.scout.ovr[0])}–${fmtStar(p.scout.ovr[1])}`}</span>`
  : stars(p.stars, lg ? "lg" : ""));
export const potText = (p) => (p.fog && p.scout ? `<span class="srange pot">${fmtStar(p.scout.pot[0])}–${fmtStar(p.scout.pot[1])}</span>` : stars(p.pstars, "pot"));
export const pos = (p) => `<span class="pos">${p}</span>`;

export function avatar(p, team, lg = false) {
  const c1 = team?.c1 || "#5a6274", c2 = team?.c2 || "#1a1d24";
  const ini = `${p.fn?.[0] || ""}${p.ln?.[0] || ""}`;
  return `<span class="avatar ${lg ? "lg" : ""}" style="background:linear-gradient(140deg, ${c2}, #07080b 85%); box-shadow: inset 0 0 0 1.5px ${c1}55; color:${c1}">${esc(ini)}<span class="num">${p.num ?? ""}</span></span>`;
}

export function injTag(p) {
  if (!p.inj) return "";
  return `<span class="inj" title="${esc(p.inj.type)}">✚${p.inj.games > 0 ? p.inj.games : "DTD"}</span>`;
}

export function pname(p, team, sub = null, withAvatar = true) {
  return `<span class="pname" data-player="${p.id}">${withAvatar ? avatar(p, team) : ""}<span><span class="nm-t">${esc(p.fn)} ${esc(p.ln)}</span>${injTag(p)}${sub !== null ? `<span class="sub">${sub}</span>` : ""}</span></span>`;
}

export function tlink(t, size = 22, full = false) {
  return `<span class="tteam" data-team="${t.tid}">${logo(t, size)}<b>${full ? esc(t.city + " " + t.name) : esc(t.abbr)}</b></span>`;
}

export function slab(title, body, { right = "", cls = "", flush = false } = {}) {
  return `<section class="slab ${flush ? "flush" : ""} ${cls}">
    ${title ? `<div class="slab-head"><span class="tag"></span><h3>${title}</h3><div class="right">${right}</div></div>` : ""}
    ${body}</section>`;
}

export function seg(name, value, options) {
  return `<div class="seg" data-seg="${name}">${options.map(([v, l]) => `<button data-v="${v}" class="${v === value ? "on" : ""}">${l}</button>`).join("")}</div>`;
}

export function sparkline(vals, w = 120, h = 30, color = "var(--acc)") {
  if (!vals.length) return "";
  const lo = Math.min(...vals) - 2, hi = Math.max(...vals) + 2;
  const pts = vals.map((v, i) => `${(i / Math.max(1, vals.length - 1)) * (w - 4) + 2},${h - 2 - ((v - lo) / (hi - lo || 1)) * (h - 4)}`);
  return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline points="${pts.join(" ")}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round"/>${pts.map((p) => `<circle cx="${p.split(",")[0]}" cy="${p.split(",")[1]}" r="2.2" fill="${color}"/>`).join("")}</svg>`;
}

export function toast(msg, err = false) {
  const root = document.getElementById("toast-root");
  const d = document.createElement("div");
  d.className = `toast ${err ? "err" : ""}`;
  d.innerHTML = esc(msg);
  root.appendChild(d);
  setTimeout(() => { d.style.opacity = "0"; d.style.transition = ".3s"; }, err ? 4200 : 2600);
  setTimeout(() => d.remove(), err ? 4600 : 3000);
}

export function perGame(st) {
  if (!st || !st.gp) return null;
  const g = st.gp;
  return {
    gp: g, gs: st.gs, min: st.min / g, pts: st.pts / g, reb: (st.orb + st.drb) / g, orb: st.orb / g, ast: st.ast / g,
    stl: st.stl / g, blk: st.blk / g, tov: st.tov / g, pf: st.pf / g, pm: st.pm / g,
    fgp: st.fga ? st.fgm / st.fga : 0, tpp: st.tpa ? st.tpm / st.tpa : 0, ftp: st.fta ? st.ftm / st.fta : 0,
    fga: st.fga / g, tpa: st.tpa / g, fta: st.fta / g,
    ts: st.fga + st.fta ? st.pts / (2 * (st.fga + 0.44 * st.fta)) : 0,
  };
}

// Timing mini-game. Needle sweeps; click (or Space) to release. acc = 0 (dead center) .. 1 (edge).
// The green window widens with the Coaching Staff upgrade. Mirrors meter_grade() on the server.
export function meterGrade(acc, coach = 0) {
  const w = 0.16 * (1 + 0.12 * coach);
  return acc <= w * 0.3 ? "perfect" : acc <= w ? "good" : acc <= w * 2.2 ? "ok" : "miss";
}
export function shotMeter(host, coach, onDone, { speed = 2.7, button = "RELEASE", hold = 650 } = {}) {
  const w = 0.16 * (1 + 0.12 * coach);
  host.innerHTML = `<div class="meter2"><div class="zone ok" style="left:${50 - w * 2.2 * 50}%;width:${w * 2.2 * 100}%"></div>
    <div class="zone good" style="left:${50 - w * 50}%;width:${w * 100}%"></div><div class="zone perfect" style="left:${50 - w * 0.3 * 50}%;width:${w * 0.3 * 100}%"></div><i class="needle"></i></div>
    <div class="row" style="margin-top:12px"><span class="label meter-grade">&nbsp;</span><span class="sp"></span><button class="btn hot lg meter-btn">${button}</button></div>`;
  const needle = host.querySelector(".needle");
  const phase = Math.random() * Math.PI * 2;
  const sp = speed * (0.9 + Math.random() * 0.25);
  let x = 0, stopped = false, raf;
  const t0 = performance.now();
  const tick = (now) => {
    x = Math.sin(phase + ((now - t0) / 1000) * sp);
    needle.style.left = `${50 + x * 50}%`;
    if (!stopped) raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
  const fire = () => {
    if (stopped) return;
    stopped = true;
    cancelAnimationFrame(raf);
    window.removeEventListener("keydown", key);
    const acc = Math.min(1, Math.abs(x));
    const grade = meterGrade(acc, coach);
    const g = host.querySelector(".meter-grade");
    g.textContent = grade.toUpperCase();
    g.className = `label meter-grade ${grade === "perfect" || grade === "good" ? "good" : grade === "ok" ? "warn" : "bad"}`;
    setTimeout(() => onDone(acc, grade), hold);
  };
  const key = (e) => { if (e.code === "Space") { e.preventDefault(); fire(); } };
  window.addEventListener("keydown", key);
  host.querySelector(".meter-btn").addEventListener("click", fire);
  host.querySelector(".meter2").addEventListener("click", fire);
}

export function moodFace(m) {
  return m >= 88 ? "🤩" : m >= 72 ? "😄" : m >= 55 ? "🙂" : m >= 38 ? "😕" : m >= 25 ? "😠" : "🤬";
}
export function moodLabel(m) {
  return m >= 88 ? "Ecstatic" : m >= 72 ? "Happy" : m >= 55 ? "Content" : m >= 38 ? "Frustrated" : m >= 25 ? "Unhappy" : "Furious";
}
export function moodChip(p) {
  const m = p.morale ?? 65;
  const col = m >= 72 ? "var(--good)" : m >= 55 ? "var(--txt)" : m >= 38 ? "var(--warn)" : "var(--bad)";
  return `<span class="mood" title="${moodLabel(m)} (${Math.round(m)})"><span>${moodFace(m)}</span><span class="mbar"><i style="width:${m}%;background:${col}"></i></span>${p.treq ? `<span class="chip bad" style="margin-left:4px">TRADE REQ</span>` : ""}</span>`;
}
export const traitChip = (p) => (p.trait ? `<span class="chip trait" title="${esc(p.trait)}">${esc(p.trait)}</span>` : "");
export function pips(n, max = 5) {
  return `<span class="pips">${Array.from({ length: max }, (_, i) => `<i class="${i < n ? "on" : ""}"></i>`).join("")}</span>`;
}

export const SHOT_COLORS = { three: "#6ae4ff", mid: "#b48cff", rim: "#ff5d3a", post: "#ffc23d" };
