// Boot, routing, app shell, landing / new-league flow, global event delegation.
import * as U from "./ui.js";
import { S, hooks, ACT, SEG, api, act, loadState, applyTheme, T, me, nextGame } from "./state.js";
import { VIEWS } from "./views.js";
import { OPS } from "./ops.js";
import { openPlayer } from "./player.js";
import { renderGame, renderLive } from "./game.js";
import { EXTRAS } from "./extras.js";

const ALL = { ...VIEWS, ...OPS, ...EXTRAS };
const root = document.getElementById("root");

// ------------------------------------------------------------------ modal
export function modal(html, cls = "", key = "") {
  const mr = document.getElementById("modal-root");
  const open = mr.querySelector(".modal-bg");
  // same card already open: update it in place (no re-open animation, scroll position kept)
  if (key && open && open.dataset.key === key) {
    const box = open.querySelector(".modal");
    const top = box.scrollTop;
    box.className = `modal ${cls}`;
    box.innerHTML = `<button class="iconbtn modal-x" data-act="close-modal">✕</button>${html}`;
    box.scrollTop = top;
    return;
  }
  mr.innerHTML = `<div class="modal-bg" data-key="${key}"><div class="modal ${cls}"><button class="iconbtn modal-x" data-act="close-modal">✕</button>${html}</div></div>`;
  mr.querySelector(".modal-bg").addEventListener("mousedown", (e) => { if (e.target.classList.contains("modal-bg")) closeModal(); });
}
export function closeModal() { document.getElementById("modal-root").innerHTML = ""; }
ACT["close-modal"] = closeModal;
window.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

// ------------------------------------------------------------------ routing
function route() {
  const h = location.hash.replace(/^#\/?/, "") || "hub";
  const [path, query] = h.split("?");
  const parts = path.split("/");
  return { name: parts[0], arg: parts[1], query: new URLSearchParams(query || "") };
}
export const go = (h) => { location.hash = h; };
window.addEventListener("hashchange", () => { document.body.classList.remove("menu-open"); render(); });
ACT["menu"] = () => document.body.classList.toggle("menu-open");

const NAV = [
  ["hub", "Hub"], ["roster", "Roster"], ["schedule", "Schedule"], ["standings", "Standings"], ["rankings", "Rankings"],
  ["stats", "Stats"], ["awards", "Award Race"],
  ["allstar", "All-Star"], ["playoffs", "Playoffs"], ["draft", "Draft"], ["trade", "Trades"], ["fa", "Free Agency"],
  ["offseason", "Offseason"], ["franchise", "Franchise"], ["teams", "League"], ["history", "History"],
];

function phaseLabel(L) {
  return { draft: L.draft?.type === "fantasy" ? "Fantasy Draft" : "Draft", regular: `Regular Season · Day ${L.day + 1}/${L.consts.days}`, playoffs: "Playoffs", offseason: "Offseason" }[L.phase] || L.phase;
}

function ticker(L) {
  const res = L.results.slice(-14).reverse();
  if (!res.length) {
    const items = L.news.slice(-6).reverse().map((n) => `<span class="tick-item">${U.esc(n.txt)}</span>`).join("");
    return `<div class="ticker"><div class="ticker-track">${items}${items}</div></div>`;
  }
  const items = res.map((r) => {
    const hw = r.hs > r.as;
    return `<span class="tick-item" data-go="#/game/${r.gid}">${r.po ? `<span class="chip hot">${r.series}</span>` : ""}
      <span class="${hw ? "l" : "w"}">${T(r.a).abbr} <b>${r.as}</b></span>
      <span class="${hw ? "w" : "l"}">${T(r.h).abbr} <b>${r.hs}</b></span>${r.ot ? `<span class="mute">OT</span>` : ""}</span>`;
  }).join("");
  return `<div class="ticker"><div class="ticker-track">${items}${items}</div></div>`;
}

function shell(content, current) {
  const L = S.L;
  const t = me();
  const t0 = me();
  const cheapest = Math.min(...L.consts.tracks.map((tr) => ((t0.upg?.[tr.key] || 0) < 5 ? L.consts.cost[t0.upg?.[tr.key] || 0] : 999)));
  const badge = {
    draft: L.phase === "draft" && L.derived.on_clock === L.user ? "!" : "",
    offseason: L.phase === "offseason" && L.resign.length ? L.resign.length : "",
    franchise: (t0.fp || 0) >= cheapest ? t0.fp : "",
    allstar: L.allstar && L.allstar.s === L.season && L.allstar.status === "ready" ? "★" : "",
    roster: L.players && Object.values(L.players).some((p) => p.tid === L.user && p.treq) ? "!" : "",
  };
  const asNow = L.allstar && L.allstar.s === L.season;
  const nav = NAV.filter(([k]) => !(k === "offseason" && L.phase !== "offseason") && !(k === "playoffs" && !L.playoffs && !L.history.length) && !(k === "allstar" && !asNow && !(L.allstar_hist || []).length) && !(k === "rankings" && !L.settings?.committee))
    .map(([k, l], i) => `<a class="nav-item ${current === k ? "on" : ""}" href="#/${k}"><span class="n">${String(i + 1).padStart(2, "0")}</span>${l}${badge[k] ? `<span class="pip">${badge[k]}</span>` : ""}</a>`).join("");
  return `<div class="shell">
    <aside class="rail">
      <div class="brand"><div class="brand-mark">9&</div><div class="brand-name">NINE &amp; DONE<small>DYNASTY SIM</small></div></div>
      <nav class="rail-nav">${nav}</nav>
      <div class="rail-foot">
        <div class="row">${U.logo(t, 30)}<div><div style="font-weight:700;font-size:12.5px">${U.esc(t.name)}</div><div class="label">${U.esc(L.name)}</div></div></div>
        <button class="btn ghost sm" data-act="exit-league">Switch League</button>
      </div>
    </aside>
    <div class="main">
      <header class="topbar">
        <button class="menu-btn" data-act="menu" aria-label="Menu">☰</button>
        <div class="phase-chip"><span class="dot"></span><span class="label" style="color:var(--txt)">${L.season} · ${phaseLabel(L)}</span></div>
        ${ticker(L)}
        <div class="cap-chip"><span class="dim">PAYROLL</span><b class="${L.derived.payroll[L.user] > L.consts.cap ? "warn" : ""}">${U.money(L.derived.payroll[L.user])}</b><span class="mute">/ ${U.money(L.consts.cap)}</span></div>
      </header>
      <div class="view">${content}</div>
    </div>
  </div>`;
}

/// ------------------------------------------------------------------ landing
const NEW = { team: 0, start: "classic", name: "", teams: 10, conf: false, committee: false };
let SAVES = null;
let META = null;

// Network once; every click after that re-renders from memory (instant).
async function renderLanding(refresh = false) {
  applyTheme();
  if (refresh || SAVES === null || META === null) {
    if (SAVES === null && META === null) root.innerHTML = `<div class="loader">LOADING</div>`;
    try { [SAVES, META] = await Promise.all([api("saves"), META ? Promise.resolve(META) : api("meta")]); } catch (e) { U.toast(e.message, true); SAVES = SAVES || []; }
  }
  drawLanding();
}

function drawLanding() {
  const teams = META?.teams || [];
  const tsel = teams[NEW.team];
  const nameVal = document.getElementById("lg-name")?.value ?? NEW.name;
  NEW.name = nameVal;
  // keep the scroll position across redraws (the setup panel scrolls inside .landing-right)
  const panelScroll = document.querySelector(".landing-right")?.scrollTop || 0;
  const pageScroll = window.scrollY;
  requestAnimationFrame(() => {
    const panel = document.querySelector(".landing-right");
    if (panel) panel.scrollTop = panelScroll;
    window.scrollTo(0, pageScroll);
  });
  const fmt = NEW.committee
    ? "A selection committee ranks teams every week and picks the four playoff teams."
    : "The top four teams by record make the playoffs.";
  root.innerHTML = `<div class="landing">
    <div class="landing-left">
      <div><div class="kicker">Basketball dynasty simulator</div>
        <div class="mega">Nine<br><span class="amp">&amp;</span> <span class="o">Done</span></div>
        <p class="dim" style="max-width:520px;font-size:16px;margin-top:26px">You're the owner, the GM and the coach. Draft, scout, negotiate and develop a roster, then survive a nine-game sprint and a best-of-five playoff bracket.</p>
      </div>
      <div class="row wrap" style="gap:28px;margin-top:40px">
        ${[["10–20", "franchises"], ["9", "game seasons"], ["BO5", "playoff series"], ["1–5★", "player ratings"]].map(([a, b]) => `<div><div class="big-num">${a}</div><div class="label" style="margin-top:6px">${b}</div></div>`).join("")}
      </div>
    </div>
    <div class="landing-right">
      ${SAVES?.length ? `<div class="label" style="margin-bottom:10px">Continue</div>
        ${SAVES.map((s) => `<div class="save-card" data-act="open-save" data-id="${s.id}">
          <div class="brand-mark" style="width:34px;height:34px;font-size:12px">${s.season % 100}</div>
          <div><div style="font-weight:700">${U.esc(s.name)}</div><div class="label">${U.esc(s.team)} · ${s.season} ${U.esc(s.phase)} · ${U.esc(s.record)}</div></div>
          <button class="iconbtn" data-act="del-save" data-id="${s.id}" title="Delete">✕</button></div>`).join("")}
        <div class="divider" style="margin:24px 0"></div>` : ""}
      <div class="label" style="margin-bottom:10px">New league · choose your franchise</div>
      <div class="team-pick big">${teams.map((t, i) => `<div class="team-tile ${i === NEW.team ? "on" : ""}" style="--tc:${t.c1}" data-act="pick-team" data-i="${i}">
        ${U.logo(t, 40)}<div><div class="ct">${U.esc(t.city.toUpperCase())}</div><div class="nm">${U.esc(t.name)}</div></div></div>`).join("")}</div>
      ${tsel ? `<div class="slab" style="margin-top:14px;--cut:10px"><div class="row">${U.logo(tsel, 54)}<div><div class="display" style="font-size:20px;font-weight:800">${U.esc(tsel.city)} ${U.esc(tsel.name)}</div><div class="label">Home: ${U.esc(tsel.arena)}</div></div></div></div>` : ""}
      <div class="label" style="margin:22px 0 4px">League setup</div>
      <div class="slab" style="--cut:10px;padding:6px 16px">
        <div class="setup-row"><span style="font-weight:700">Rosters</span>${U.seg("nl-start", NEW.start, [["classic", "Pre-built + rookie draft"], ["fantasy", "Fantasy draft"]])}
          <div class="hint">${NEW.start === "fantasy" ? "Every player goes into one pool. Build from nothing over a 13-round snake draft." : "Teams start with balanced rosters. The season opens with a two-round rookie draft."}</div></div>
        <div class="setup-row"><span style="font-weight:700">Teams</span>${U.seg("nl-teams", String(NEW.teams), [10, 12, 14, 16, 18, 20].map((n) => [String(n), String(n)]))}
          <div class="hint">Four teams make the playoffs: semifinals and Finals, both best-of-five.</div></div>
        <div class="setup-row"><span style="font-weight:700">Selection committee</span><div class="row"><div class="toggle ${NEW.committee ? "on" : ""}" data-act="nl-toggle" data-k="committee"></div><span class="dim" style="font-size:12.5px">${NEW.committee ? "CFP-style rankings" : "Standings decide"}</span></div>
          <div class="hint">${fmt}</div></div>
      </div>
      <div class="label" style="margin:22px 0 10px">League name</div>
      <input id="lg-name" style="width:100%" placeholder="Nine & Done League" value="${U.esc(NEW.name)}">
      <button class="btn pri lg" style="width:100%;margin-top:22px" data-act="create-league">Tip off →</button>
    </div></div>`;
}
ACT["pick-team"] = (el) => { NEW.team = +el.dataset.i; drawLanding(); };
ACT["nl-toggle"] = (el) => { NEW[el.dataset.k] = !NEW[el.dataset.k]; drawLanding(); };
SEG["nl-start"] = (v) => { NEW.start = v; drawLanding(); };
SEG["nl-teams"] = (v) => { NEW.teams = +v; drawLanding(); };
ACT["open-save"] = async (el, e) => {
  if (e.target.closest("[data-act='del-save']")) return;
  S.sid = +el.dataset.id; localStorage.setItem("nd_sid", S.sid);
  await boot("#/hub");
};
ACT["del-save"] = async (el, e) => {
  e.stopPropagation();
  if (!confirm("Delete this league permanently?")) return;
  await api(`saves/${el.dataset.id}`, null, "DELETE");
  if (S.sid === +el.dataset.id) { S.sid = null; localStorage.removeItem("nd_sid"); }
  SAVES = SAVES.filter((s) => s.id !== +el.dataset.id);
  drawLanding();
};
ACT["create-league"] = async () => {
  const name = document.getElementById("lg-name").value.trim();
  root.innerHTML = `<div class="loader">GENERATING LEAGUE</div>`;
  try {
    const r = await api("saves", { name, team: NEW.team, settings: { teams: NEW.teams, committee: NEW.committee, start: NEW.start } });
    S.sid = r.id; localStorage.setItem("nd_sid", S.sid);
    SAVES = null;
    await boot("#/draft");
  } catch (e) { U.toast(e.message, true); drawLanding(); }
};
ACT["exit-league"] = () => { S.sid = null; S.L = null; SAVES = null; localStorage.removeItem("nd_sid"); location.hash = ""; render(); };


// ------------------------------------------------------------------ render
let lastRoute = "";
export function render() {
  if (!S.sid || !S.L) { renderLanding(); return; }
  const r = route();
  if (r.name === "game") {
    renderGame(root, r.arg, r.query.get("watch") === "1");
    return;
  }
  if (r.name === "live") {
    renderLive(root);
    return;
  }
  const v = ALL[r.name] || ALL.hub;
  const key = ALL[r.name] ? r.name : "hub";
  const same = lastRoute === location.hash;
  const railTop = root.querySelector(".rail-nav")?.scrollTop || 0;   // the nav keeps its place across pages
  const scrollY = same ? window.scrollY : 0;
  // inner scroll boxes (prospect board, tables, nav rail) keep their position across redraws
  const inner = same ? [...root.querySelectorAll(".tbl-wrap, .rail-nav, [data-keep-scroll]")].map((el) => [el.scrollTop, el.scrollLeft]) : [];
  root.innerHTML = shell(v(r), key);
  root.querySelectorAll(".tbl-wrap, .rail-nav, [data-keep-scroll]").forEach((el, i) => {
    if (inner[i]) { el.scrollTop = inner[i][0]; el.scrollLeft = inner[i][1]; }
  });
  const rail = root.querySelector(".rail-nav");
  if (rail) rail.scrollTop = railTop;
  // an open player card refreshes in place after any action
  const card = document.querySelector("#modal-root .modal-bg[data-key^='p:']");
  if (card) openPlayer(+card.dataset.key.slice(2));
  lastRoute = location.hash;
  window.scrollTo(0, scrollY);
  ALL[`${key}_mount`]?.(r);
  if (r.query.get("p")) openPlayer(+r.query.get("p"));
}
hooks.render = render;

// ------------------------------------------------------------------ delegation
document.addEventListener("click", (e) => {
  const segBtn = e.target.closest("[data-seg] button");
  if (segBtn) {
    const name = segBtn.parentElement.dataset.seg;
    SEG[name]?.(segBtn.dataset.v, segBtn);
    return;
  }
  const a = e.target.closest("[data-act]");
  if (a && ACT[a.dataset.act]) { e.preventDefault(); ACT[a.dataset.act](a, e); return; }
  const p = e.target.closest("[data-player]");
  if (p) { openPlayer(+p.dataset.player); return; }
  const t = e.target.closest("[data-team]");
  if (t) { closeModal(); go(`#/team/${t.dataset.team}`); return; }
  const g = e.target.closest("[data-go]");
  if (g) { closeModal(); go(g.dataset.go); }
});

async function boot(hash) {
  if (!S.sid) { renderLanding(); return; }
  root.innerHTML = `<div class="loader">LOADING LEAGUE</div>`;
  try {
    await loadState();
  } catch (e) {
    S.sid = null; localStorage.removeItem("nd_sid");
    renderLanding();
    return;
  }
  if (hash && location.hash !== hash) { location.hash = hash; return; }
  render();
}
boot();
