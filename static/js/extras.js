// Franchise upgrades, All-Star Weekend (with a playable 3-point contest), rivalry boards.
import * as U from "./ui.js";
import { S, ACT, act, hooks, T, Pl, me } from "./state.js";

const render = () => hooks.render();
const head = (kicker, title, sub = "", right = "") => `<div class="view-head"><div><div class="kicker">${kicker}</div><h1>${title}</h1>${sub ? `<div class="sub">${sub}</div>` : ""}</div><div class="right">${right}</div></div>`;
const ICONS = { dev: "📈", arena: "🏟️", medical: "🩺", conditioning: "🫀", analytics: "📊", scouting: "🔭", culture: "🤝", frontoffice: "💼", coaching: "📋" };

// ================================================================== FRANCHISE / UPGRADES
function franchise() {
  const L = S.L, t = me();
  const tracks = L.consts.tracks, cost = L.consts.cost;
  const fp = t.fp || 0;
  const cards = tracks.map((tr) => {
    const lv = t.upg?.[tr.key] || 0;
    const max = lv >= 5;
    const c = max ? null : cost[lv];
    const can = !max && fp >= c;
    return `<section class="slab upg ${max ? "maxed" : ""}">
      <div class="row"><span class="upg-ico">${ICONS[tr.key] || "◆"}</span><div><h3 style="font-size:14px;font-family:var(--display)">${U.esc(tr.name)}</h3>${U.pips(lv)}</div><span class="sp"></span><span class="big-num" style="font-size:20px"><span class="label">LV</span> ${lv}</span></div>
      <p class="dim" style="font-size:12.5px;margin:10px 0">${U.esc(tr.desc)}</p>
      <div class="upg-fx"><div class="label">Now</div><div class="mono">${lv ? U.esc(tr.fx[lv]) : "—"}</div></div>
      ${max ? `<div class="upg-fx"><div class="label acc">Maxed out</div></div>` : `<div class="upg-fx next"><div class="label">Next level</div><div class="mono acc">${U.esc(tr.fx[lv + 1])}</div></div>`}
      <button class="btn ${can ? "pri" : ""}" style="width:100%;margin-top:12px" data-act="buy-upg" data-k="${tr.key}" ${can ? "" : "disabled"}>${max ? "MAX" : `Upgrade · ${c} FP`}</button>
    </section>`;
  }).join("");
  const log = (t.fp_log || []).slice().reverse().slice(0, 14);
  const keys = tracks.map((x) => x.key);
  const league = L.teams.slice().sort((a, b) => Object.values(b.upg || {}).reduce((x, y) => x + y, 0) - Object.values(a.upg || {}).reduce((x, y) => x + y, 0));
  return head("Owner's suite", "Franchise HQ", "Earn franchise points (FP) by winning games, rivalries, playoff series, awards and live-coaching challenges. Spend them on nine upgrade tracks. You can't max everything, so choose what kind of franchise you're building.",
    `<div class="fp-badge"><div class="label">Franchise points</div><div class="big-num">${fp}</div></div>`) +
    `<div class="grid g3" style="margin-bottom:16px">${cards}</div>
    <div class="grid g2">
      ${U.slab("How you earn FP", `<table class="tbl compact"><tbody>
        ${[["Regular-season win", "+3"], ["Regular-season loss", "+1"], ["Rivalry win (Heated or hotter)", "+2"], ["Playoff game win", "+2"], ["Playoff series win", "+6"], ["Championship", "+15"], ["Player award (MVP, All-League…)", "+3 each"], ["All-Star selection", "+2 each"], ["All-Star contest winner", "+1–2"], ["Live-coaching calls won", "+1 each (max 3/game)"]].map(([a, b]) => `<tr><td class="l" style="font-family:var(--body)">${a}</td><td class="hl">${b}</td></tr>`).join("")}
      </tbody></table>`)}
      ${U.slab("Recent earnings", log.length ? log.map((x) => `<div class="row" style="padding:6px 0;border-bottom:1px solid var(--line)"><span class="mono acc" style="width:40px">+${x.n}</span><span>${U.esc(x.txt)}</span><span class="sp"></span><span class="label">${x.s}</span></div>`).join("") : `<div class="empty">Win some games</div>`)}
    </div>
    <div style="height:16px"></div>
    ${U.slab("League facilities", `<div class="tbl-wrap"><table class="tbl compact"><thead><tr><th class="l">Team</th>${tracks.map((x) => `<th class="c" title="${U.esc(x.name)}">${ICONS[x.key]}</th>`).join("")}<th>Total</th></tr></thead><tbody>
      ${league.map((tm) => `<tr class="${tm.tid === L.user ? "me" : ""}"><td class="l">${U.tlink(tm, 18)}</td>${keys.map((k) => `<td class="c">${tm.upg?.[k] || 0}</td>`).join("")}<td class="hl">${Object.values(tm.upg || {}).reduce((x, y) => x + y, 0)}</td></tr>`).join("")}
    </tbody></table></div><div class="dim" style="font-size:12px;margin-top:8px">AI teams earn and spend FP too. Arena, Analytics and Player Development edges are measured against the league average, so keeping up matters.</div>`)}`;
}
ACT["buy-upg"] = (el) => act("upgrade", { key: el.dataset.k }, { label: "BUILDING" }).then(() => U.toast("Upgrade complete!"));

// ================================================================== ALL-STAR
function nameOf(pid) {
  const p = Pl(pid);
  return p ? p : null;
}
function playerLine(pid, extra = "") {
  const p = nameOf(pid);
  if (!p) return `<div class="mute">Retired</div>`;
  return `<div class="row" style="padding:5px 0">${U.ovrBadge(p)}${U.pname(p, T(p.tid), `${T(p.tid).abbr} · ${p.pos}`, false)}<span class="sp"></span>${p.tid === S.L.user ? `<span class="chip acc">YOURS</span>` : ""}${extra}</div>`;
}

function allstar() {
  const L = S.L, a = L.allstar;
  const hist = (L.allstar_hist || []).slice().reverse();
  const histSlab = U.slab("All-Star history", hist.length ? `<table class="tbl compact"><thead><tr><th class="l">Season</th><th class="l">ASG MVP</th><th class="l">3-Point</th><th class="l">Dunk</th><th>Score</th></tr></thead><tbody>${hist.map((h) => `<tr><td class="l">${h.s}</td><td class="l nm">${U.esc(h.mvp)}</td><td class="l nm">${U.esc(h.three)}</td><td class="l nm">${U.esc(h.dunk)}</td><td>${Math.max(...h.score)}–${Math.min(...h.score)}</td></tr>`).join("")}</tbody></table>` : `<div class="empty">No All-Star weekends yet</div>`);
  if (!a || a.s !== L.season) {
    return head("Mid-season", "All-Star Weekend", `The break comes after game ${L.consts.allstar_day}. The 14 best players are selected, plus a 3-Point Contest, a Dunk Contest and the All-Star Game.`) + histSlab;
  }
  const teams = L.consts.as_teams;
  const th = a.three, dk = a.dunk;
  const sc = (obj, pid) => obj[String(pid)];
  const threeTable = (round, ids) => ids.map((pid) => { const r = sc(th[round], pid); return playerLine(pid, r ? `<span class="big-num" style="font-size:18px;margin-left:10px">${r.score}</span>${r.you ? `<span class="chip volt">YOU SHOT</span>` : ""}` : ""); }).join("");
  let threeBody;
  if (S.ui.threeGame) threeBody = `<div id="three-game"></div>`;
  else if (L.derived.three_pending) {
    threeBody = `${th.stage === "r1" ? threeTable("r1", th.entrants) : threeTable("r1", th.finalists)}
      <div class="slab glow" style="margin-top:12px"><div class="display" style="font-size:16px;font-weight:800">Your shooter is up${th.stage === "final" ? " in the FINAL" : ""}!</div>
      <p class="dim" style="margin:6px 0 12px">25 shots in 5 racks, and the last ball of each rack is worth 2. Time each release on the meter. Better timing means more makes.</p>
      <button class="btn pri lg" data-act="three-start">Take your shots →</button></div>`;
  } else if (th.stage === "r1") threeBody = th.entrants.map((pid) => playerLine(pid)).join("");
  else threeBody = `<div class="label">Round 1</div>${threeTable("r1", th.entrants)}${th.stage === "done" ? `<div class="label" style="margin-top:12px">Final</div>${threeTable("final", th.finalists)}` : ""}`;
  const dunkBody = dk.winner ? dk.entrants.map((pid) => playerLine(pid, `<span class="mono" style="margin-left:10px">${(dk.r1[String(pid)] || []).join(" + ")}${dk.final[String(pid)] ? ` · F ${dk.final[String(pid)].join(" + ")}` : ""}</span>${dk.winner === pid ? " 🏆" : ""}`)).join("") : dk.entrants.map((pid) => playerLine(pid)).join("");
  const done = a.status === "done";
  return head(`${L.season} · mid-season`, "All-Star Weekend", done ? "The weekend is in the books." : "The league's best, on one stage. Shoot your round if you have someone in the 3-Point Contest, then run the rest of the weekend.",
    done ? `<button class="btn pri" data-go="#/game/${a.gid}?watch=1">▶ Watch the All-Star Game</button>` : `<button class="btn pri" data-act="as-run" ${L.derived.three_pending || S.ui.threeGame ? "disabled" : ""}>Run the weekend →</button>`) +
    (done ? `<section class="slab glow hero" style="margin-bottom:16px"><div class="row">${U.logo(teams[1], 64)}<span class="big-num">${a.score[1]}</span><span class="mute">–</span><span class="big-num">${a.score[0]}</span>${U.logo(teams[0], 64)}</div>
      <div><div class="kicker">All-Star Game MVP</div>${playerLine(a.mvp)}</div><div><button class="btn" data-go="#/game/${a.gid}">Box score</button></div></section>` : "") +
    `<div class="grid g2" style="margin-bottom:16px">${[0, 1].map((i) => U.slab(`Team ${teams[i].name}`, a.teams[i].map((pid) => playerLine(pid)).join(""), { right: U.logo(teams[i], 26) })).join("")}</div>
    <div class="grid g2" style="margin-bottom:16px">
      ${U.slab(`3-Point Contest${th.winner ? " · 🏆 " + U.esc(Pl(th.winner)?.ln || "") : ""}`, threeBody)}
      ${U.slab(`Dunk Contest${dk.winner ? " · 🏆 " + U.esc(Pl(dk.winner)?.ln || "") : ""}`, dunkBody)}
    </div>` + histSlab;
}

ACT["as-run"] = () => act("allstar_run", {}, { label: "ALL-STAR WEEKEND" });
ACT["three-start"] = () => {
  S.ui.threeGame = { accs: [] };
  render();
  nextThreeShot();
};
function nextThreeShot() {
  const host = document.getElementById("three-game");
  const st = S.ui.threeGame;
  if (!host || !st) return;
  const i = st.accs.length;
  const coach = me().upg?.coaching || 0;
  const racks = Array.from({ length: 5 }, (_, r) => `<div class="rack">${Array.from({ length: 5 }, (_, b) => {
    const k = r * 5 + b;
    const g = st.grades?.[k];
    return `<i class="ball ${b === 4 ? "money" : ""} ${g ? (g === "perfect" || g === "good" ? "hit" : g === "ok" ? "mid" : "miss") : ""} ${k === i ? "cur" : ""}"></i>`;
  }).join("")}</div>`).join("");
  host.innerHTML = `<div class="racks">${racks}</div><div class="label" style="margin:10px 0 6px">Shot ${i + 1} of 25${i % 5 === 4 ? " · MONEY BALL (2 pts)" : ""}</div><div id="three-meter"></div>`;
  U.shotMeter(document.getElementById("three-meter"), coach, (acc, grade) => {
    st.accs.push(acc);
    (st.grades = st.grades || []).push(grade);
    if (st.accs.length >= 25) {
      const accs = st.accs;
      S.ui.threeGame = null;
      act("allstar_three", { accs }, { label: "COUNTING THE MAKES" }).then(() => {
        const th = S.L.allstar.three;
        const mine = Object.values(th.final || {}).find((r) => r.you) || Object.values(th.r1 || {}).find((r) => r.you);
        if (mine) U.toast(`Your round: ${mine.score} points`);
      });
    } else nextThreeShot();
  }, { speed: 3.4, button: "SHOOT", hold: 260 });
}

// ================================================================== RIVALRIES
export function rivalryList(filterTid = null, limit = 12) {
  const L = S.L;
  const rows = Object.entries(L.rivals || {}).map(([k, r]) => ({ k, r, ids: k.split("-").map(Number) }))
    .filter((x) => filterTid === null ? x.r.score >= 20 : x.ids.includes(filterTid) && (x.r.score >= 8 || x.r.name))
    .sort((a, b) => b.r.score - a.r.score).slice(0, limit);
  if (!rows.length) return `<div class="empty">No rivalries yet. They grow from close games, overtime and playoff series.</div>`;
  const tierCls = ["", "ice", "hot", "bad"];
  return rows.map(({ r, ids }) => {
    const [a, b] = ids;
    const tier = r.score >= 75 ? 3 : r.score >= 45 ? 2 : r.score >= 20 ? 1 : 0;
    return `<div class="rival-row ${ids.includes(L.user) ? "mine" : ""}">
      <div class="row">${U.tlink(T(a), 22)}<span class="mono dim">${r.w[a] || 0}–${r.w[b] || 0}</span>${U.tlink(T(b), 22)}<span class="sp"></span><span class="chip ${tierCls[tier]}">${tier ? "🔥 " : ""}${L.consts.tiers[tier]}</span></div>
      <div class="row" style="margin-top:6px">${r.name ? `<span class="label acc">${U.esc(r.name)}</span>` : ""}<span class="sp"></span><span class="label">${r.g} game${r.g === 1 ? "" : "s"}${r.po ? ` · ${r.po} playoff series` : ""}</span></div>
      <div class="heat"><i style="width:${Math.min(100, r.score)}%"></i></div></div>`;
  }).join("");
}

export function rivalryBadge(a, b) {
  const r = S.L.rivals?.[`${Math.min(a, b)}-${Math.max(a, b)}`];
  if (!r) return "";
  const tier = r.score >= 75 ? 3 : r.score >= 45 ? 2 : r.score >= 20 ? 1 : 0;
  if (!tier) return "";
  return `<span class="chip ${["", "ice", "hot", "bad"][tier]}">🔥 ${S.L.consts.tiers[tier]} rivalry${r.name ? " · " + U.esc(r.name) : ""} · ${r.w[a] || 0}–${r.w[b] || 0}</span>`;
}

export const EXTRAS = { franchise, allstar, allstar_mount: () => { if (S.ui.threeGame) nextThreeShot(); } };
