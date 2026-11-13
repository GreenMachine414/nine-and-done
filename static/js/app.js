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
export function modal(html, cls = "") {
  const mr = document.getElementById("modal-root");
  mr.innerHTML = `<div class="modal-bg"><div class="modal ${cls}"><button class="iconbtn modal-x" data-act="close-modal">✕</button>${html}</div></div>`;
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
window.addEventListener("hashchange", () => render());

const NAV = [
  ["hub", "Hub"], ["roster", "Roster"], ["schedule", "Schedule"], ["standings", "Standings"], ["stats", "Stats"],
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
  const nav = NAV.filter(([k]) => !(k === "offseason" && L.phase !== "offseason") && !(k === "playoffs" && !L.playoffs && !L.history.length) && !(k === "allstar" && !asNow && !(L.allstar_hist || []).length))
    .map(([k, l], i) => `<a class="nav-item ${current === k ? "on" : ""}" href="#/${k}"><span class="n">${String(i + 1).padStart(2, "0")}</span>${l}${badge[k] ? `<span class="pip">${badge[k]}</span>` : ""}</a>`).join("");
  return `<div class="shell">
    <aside class="rail">
      <div class="brand"><div class="brand-mark">9&</div><div class="brand-name">NINE &amp; DONE<small>DYNASTY SIM</small></div></div>
      ${nav}
      <div class="rail-foot">
        <div class="row">${U.logo(t, 30)}<div><div style="font-weight:700;font-size:12.5px">${U.esc(t.name)}</div><div class="label">${U.esc(L.name)}</div></div></div>
        <button class="btn ghost sm" data-act="exit-league">Switch League</button>
      </div>
    </aside>
    <div class="main">
      <header class="topbar">
        <div class="phase-chip"><span class="dot"></span><span class="label" style="color:var(--txt)">${L.season} · ${phaseLabel(L)}</span></div>
        ${ticker(L)}
        <div class="cap-chip"><span class="dim">PAYROLL</span><b class="${L.derived.payroll[L.user] > L.consts.cap ? "warn" : ""}">${U.money(L.derived.payroll[L.user])}</b><span class="mute">/ ${U.money(L.consts.cap)}</span></div>
      </header>
      <div class="view">${content}</div>
    </div>
  </div>`;
}

// ------------------------------------------------------------------ landing
const NEW = { team: 0, mode: "classic", name: "" };
let SAVES = [];
let META = null;

async function renderLanding() {
  applyTheme();
  try { [SAVES, META] = await Promise.all([api("saves"), META ? Promise.resolve(META) : api("meta")]); } catch (e) { U.toast(e.message, true); }
  const teams = META?.teams || [];
  const tsel = teams[NEW.team];
  root.innerHTML = `<div class="landing">
    <div class="landing-left">
      <div><div class="kicker">Basketball dynasty simulator</div>
        <div class="mega">Nine<br><span class="amp">&amp;</span> <span class="o">Done</span></div>
        <p class="dim" style="max-width:520px;font-size:16px;margin-top:26px">You're the owner, the GM and the coach. Draft, trade and develop a roster, then survive a nine-game sprint. The top four go to the playoffs: two best-of-five rounds, one trophy.</p>
      </div>
      <div class="row wrap" style="gap:28px;margin-top:40px">
        ${[["10", "franchises"], ["9", "game seasons"], ["BO5", "playoff series"], ["1–5★", "player ratings"]].map(([a, b]) => `<div><div class="big-num">${a}</div><div class="label" style="margin-top:6px">${b}</div></div>`).join("")}
      </div>
    </div>
    <div class="landing-right">
      ${SAVES.length ? `<div class="label" style="margin-bottom:10px">Continue</div>
        ${SAVES.map((s) => `<div class="save-card" data-act="open-save" data-id="${s.id}">
          <div class="brand-mark" style="width:34px;height:34px;font-size:12px">${s.season % 100}</div>
          <div><div style="font-weight:700">${U.esc(s.name)}</div><div class="label">${U.esc(s.team)} · ${s.season} ${U.esc(s.phase)} · ${U.esc(s.record)}</div></div>
          <button class="iconbtn" data-act="del-save" data-id="${s.id}" title="Delete">✕</button></div>`).join("")}
        <div class="divider" style="margin:24px 0"></div>` : ""}
      <div class="label" style="margin-bottom:10px">New league · choose your franchise</div>
      <div class="team-pick">${teams.map((t, i) => `<div class="team-tile ${i === NEW.team ? "on" : ""}" style="--tc:${t.c1}" data-act="pick-team" data-i="${i}">
        ${U.logo(t, 46)}<div><div class="ct">${U.esc(t.city.toUpperCase())}</div><div class="nm">${U.esc(t.name)}</div></div></div>`).join("")}</div>
      ${tsel ? `<div class="slab" style="margin-top:14px;--cut:10px"><div class="row">${U.logo(tsel, 54)}<div><div class="display" style="font-size:20px;font-weight:800">${U.esc(tsel.city)} ${U.esc(tsel.name)}</div><div class="label">Home: ${U.esc(tsel.arena)}</div></div></div></div>` : ""}
      <div class="label" style="margin:22px 0 10px">League mode</div>
      <div class="grid g2">
        <div class="mode-card ${NEW.mode === "classic" ? "on" : ""}" data-act="pick-mode" data-m="classic"><h3>Classic</h3><p>Rosters come pre-built. The season opens with a two-round rookie draft.</p></div>
        <div class="mode-card ${NEW.mode === "fantasy" ? "on" : ""}" data-act="pick-mode" data-m="fantasy"><h3>Fantasy Draft</h3><p>Every player goes into one pool. Build your team from nothing over a 13-round snake draft.</p></div>
      </div>
      <div class="label" style="margin:22px 0 10px">League name</div>
      <input id="lg-name" style="width:100%" placeholder="Nine & Done League" value="${U.esc(NEW.name)}">
      <button class="btn pri lg" style="width:100%;margin-top:22px" data-act="create-league">Tip off →</button>
    </div></div>`;
}
ACT["pick-team"] = (el) => { NEW.name = document.getElementById("lg-name")?.value || ""; NEW.team = +el.dataset.i; renderLanding(); };
ACT["pick-mode"] = (el) => { NEW.name = document.getElementById("lg-name")?.value || ""; NEW.mode = el.dataset.m; renderLanding(); };
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
  renderLanding();
};
ACT["create-league"] = async () => {
  const name = document.getElementById("lg-name").value.trim();
  root.innerHTML = `<div class="loader">GENERATING LEAGUE</div>`;
  try {
    const r = await api("saves", { name, team: NEW.team, mode: NEW.mode });
    S.sid = r.id; localStorage.setItem("nd_sid", S.sid);
    await boot("#/draft");
  } catch (e) { U.toast(e.message, true); renderLanding(); }
};
ACT["exit-league"] = () => { S.sid = null; S.L = null; localStorage.removeItem("nd_sid"); location.hash = ""; render(); };

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
  const scrollY = lastRoute === location.hash ? window.scrollY : 0;
  root.innerHTML = shell(v(r), key);
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
