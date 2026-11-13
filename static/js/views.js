// Core pages: hub, roster/lineup/strategy, schedule, standings, stats, playoffs, league, team, history.
import * as U from "./ui.js";
import { S, ACT, SEG, act, hooks, T, Pl, me, roster, lineupOf, seasonKey, recordStr, nextGame } from "./state.js";
import { rivalryList, rivalryBadge } from "./extras.js";

const go = (h) => { location.hash = h; };
const head = (kicker, title, sub = "", right = "") => `<div class="view-head"><div><div class="kicker">${kicker}</div><h1>${title}</h1>${sub ? `<div class="sub">${sub}</div>` : ""}</div><div class="right">${right}</div></div>`;
const pg = (p, po = false) => U.perGame(p.stats?.[seasonKey(po)]);
const streak = (s) => (s > 0 ? `<span class="good">W${s}</span>` : s < 0 ? `<span class="bad">L${-s}</span>` : "—");
const modeChip = (m) => ({ contend: `<span class="chip volt">Contender</span>`, rebuild: `<span class="chip ice">Rebuild</span>`, neutral: `<span class="chip">Middle</span>` }[m]);

// ================================================================== HUB
function phaseHero() {
  const L = S.L;
  if (L.phase === "draft") {
    const d = L.draft, oc = L.derived.on_clock, slot = d.order[d.cur];
    return U.slab("Draft night", `<div class="row wrap" style="gap:20px">
      <div><div class="label">On the clock</div><div class="row" style="margin-top:8px">${U.logo(T(oc), 44)}<div><div class="display" style="font-size:20px;font-weight:800">${U.esc(T(oc).city)} ${U.esc(T(oc).name)}</div><div class="label">Pick #${slot.no} · Round ${slot.rd}</div></div></div></div>
      <div class="sp"></div><button class="btn pri lg" data-go="#/draft">${oc === L.user ? "You're up: make your pick" : "Enter the draft room"} →</button></div>`, { cls: "glow" });
  }
  if (L.phase === "offseason") {
    return U.slab("Offseason", `<div class="row wrap" style="gap:20px"><div><div class="display" style="font-size:22px;font-weight:800">The ${L.season} season is in the books.</div>
      <div class="dim" style="margin-top:6px">${L.resign.length ? `${L.resign.length} of your players need new contracts.` : "Your roster is set."} Check player progression, re-sign your guys, then shop free agency.</div></div>
      <div class="sp"></div><button class="btn pri lg" data-go="#/offseason">Offseason HQ →</button></div>`, { cls: "glow" });
  }
  if (L.derived.live) {
    return U.slab("Live game in progress", `<div class="row wrap" style="gap:20px"><div><div class="display" style="font-size:20px;font-weight:800">You stepped away from the sideline.</div>
      <div class="dim" style="margin-top:6px">Your game is paused right where you left it.</div></div><div class="sp"></div>
      <button class="btn pri lg" data-go="#/live">Back to the bench →</button></div>`, { cls: "glow" });
  }
  if (L.phase === "regular" && L.allstar && L.allstar.s === L.season && L.allstar.status === "ready") {
    return U.slab("All-Star Weekend", `<div class="row wrap" style="gap:20px"><div><div class="display" style="font-size:22px;font-weight:800">★ The All-Star break is here</div>
      <div class="dim" style="margin-top:6px">${L.derived.three_pending ? "Your player is in the 3-Point Contest, so you'll shoot his round yourself." : "See who made it, then run the contests and the game."} Simming your next game runs the weekend automatically.</div></div>
      <div class="sp"></div><button class="btn pri lg" data-go="#/allstar">Go to All-Star Weekend →</button></div>`, { cls: "glow" });
  }
  const ng = nextGame();
  const simBtns = L.phase === "regular"
    ? `<button class="btn ghost sm" data-act="sim-until" data-u="deadline" ${L.day >= L.consts.deadline ? "disabled" : ""}>Sim to deadline</button><button class="btn ghost sm" data-act="sim-until" data-u="playoffs">Sim to playoffs</button>`
    : `<button class="btn ghost sm" data-act="sim-until" data-u="champion">Sim to champion</button>`;
  if (!ng) {
    return U.slab(L.phase === "playoffs" ? "Playoffs" : "Up next", `<div class="row wrap"><div class="display" style="font-size:18px;font-weight:700">${L.phase === "playoffs" ? "Your season is over. The playoffs go on without you." : "No game scheduled."}</div><div class="sp"></div>
      <button class="btn pri" data-act="sim-day">Sim next day</button>${simBtns}</div>`, { cls: "glow" });
  }
  const h = T(ng.home), a = T(ng.away);
  const side = (t) => `<div class="side">${U.logo(t, 74)}<div class="tn">${U.esc(t.name)}</div><div class="rec">${recordStr(t)} · OVR ${S.L.derived.strength[t.tid]}</div></div>`;
  const rb = rivalryBadge(ng.home, ng.away);
  return U.slab(ng.label, `<div class="grid" style="grid-template-columns:1.3fr 1fr;gap:26px;align-items:center">
    <div><div class="matchup">${side(a)}<div class="vs">@</div>${side(h)}</div>${rb ? `<div class="row" style="justify-content:center;margin-top:14px">${rb}</div>` : ""}</div>
    <div class="col" style="gap:10px">
      <div class="label">${U.esc(h.arena)}</div>
      <button class="btn pri lg" data-go="#/live" title="Coach it yourself: timeouts, subs, huddles, defensive reads, final plays">🎙 Coach live</button>
      <div class="row" style="gap:8px"><button class="btn lg" style="flex:1" data-act="watch">▶ Watch</button><button class="btn lg" style="flex:1" data-act="sim-day">Sim</button></div>
      <div class="row wrap">${simBtns}</div>
    </div></div>`, { cls: "glow" });
}

function leadersMini(key, n = 1) {
  const L = S.L;
  const rows = Object.values(L.players).filter((p) => p.tid >= 0 && p.stats?.[key]?.gp >= Math.min(3, L.day || 1)).map((p) => ({ p, s: U.perGame(p.stats[key]) }));
  const cats = [["PTS", "pts"], ["REB", "reb"], ["AST", "ast"], ["STL", "stl"], ["BLK", "blk"]];
  if (!rows.length) return `<div class="empty">No games played yet</div>`;
  return cats.map(([lab, k]) => {
    const top = rows.slice().sort((a, b) => b.s[k] - a.s[k])[0];
    return `<div class="leader-card"><div class="cat">${lab}</div>${U.pname(top.p, T(top.p.tid), `${T(top.p.tid).abbr} · ${top.p.pos}`)}<div class="val">${U.f1(top.s[k])}</div></div>`;
  }).join("");
}

function standingsMini() {
  const L = S.L;
  return `<table class="tbl compact"><thead><tr><th class="l">#</th><th class="l">Team</th><th>W-L</th><th>Diff</th><th>Strk</th></tr></thead><tbody>
    ${L.derived.standings.map((tid, i) => { const t = T(tid); return `<tr class="${tid === L.user ? "me" : ""} ${i === 3 ? "cutline" : ""}"><td class="l mute">${i + 1}</td><td class="l">${U.tlink(t, 20)}</td><td class="hl">${t.w}-${t.l}</td><td>${U.sign(t.pf - t.pa)}</td><td>${streak(t.streak)}</td></tr>`; }).join("")}
  </tbody></table>`;
}

function newsFeed(n = 14, filterMine = false) {
  const L = S.L;
  const items = L.news.slice().reverse().filter((x) => !filterMine || x.tid === L.user).slice(0, n);
  if (!items.length) return `<div class="empty">Quiet around the league</div>`;
  return items.map((x) => `<div class="news-item nk-${x.k}"><div class="when">${x.s}<br>${x.ph === "regular" ? "D" + (x.d + 1) : x.ph.slice(0, 4).toUpperCase()}</div><div class="txt">${U.esc(x.txt)}</div></div>`).join("");
}

function lastResult() {
  const L = S.L;
  const r = L.results.slice().reverse().find((g) => g.h === L.user || g.a === L.user);
  if (!r) return "";
  const won = (r.h === L.user) === (r.hs > r.as);
  const pog = Pl(r.pog);
  return U.slab("Last game", `<div class="row" style="justify-content:space-between">
    <div class="row">${U.logo(T(r.a), 34)}<span class="big-num" style="font-size:28px">${r.as}</span><span class="mute">–</span><span class="big-num" style="font-size:28px">${r.hs}</span>${U.logo(T(r.h), 34)}</div>
    <span class="chip ${won ? "good" : "bad"}">${won ? "W" : "L"}${r.ot ? " · OT" : ""}</span></div>
    ${pog ? `<div class="label" style="margin-top:14px">Player of the game</div><div style="margin-top:6px">${U.pname(pog, T(pog.tid), T(pog.tid).abbr)}</div>` : ""}
    <button class="btn ghost sm" style="margin-top:14px;width:100%" data-go="#/game/${r.gid}">Box score & replay</button>`);
}

function hub() {
  const L = S.L, t = me();
  const rank = L.derived.standings.indexOf(L.user) + 1;
  const myLeaders = roster(L.user).map((p) => ({ p, s: pg(p) })).filter((x) => x.s);
  const top = myLeaders.sort((a, b) => b.s.pts - a.s.pts).slice(0, 3);
  return `
    <section class="slab hero" style="margin-bottom:16px;--cut:22px">
      ${U.logo(t, 116)}
      <div><div class="hero-name"><span class="city">${U.esc(t.city)}</span>${U.esc(t.name)}</div>
        <div class="hero-stats">
          <div><div class="label">Record</div><div class="v">${recordStr(t)}</div></div>
          <div><div class="label">Standing</div><div class="v">#${rank}</div></div>
          <div><div class="label">Streak</div><div class="v">${streak(t.streak)}</div></div>
          <div><div class="label">Team OVR</div><div class="v">${L.derived.strength[L.user]}</div></div>
          <div><div class="label">Chemistry</div><div class="v">${L.derived.chem[L.user]}</div></div>
          <div><div class="label">Franchise pts</div><div class="v"><a href="#/franchise" class="acc">${t.fp || 0}</a></div></div>
          <div><div class="label">Titles</div><div class="v">${t.titles || 0}</div></div>
        </div></div>
      <div class="col" style="align-items:flex-end">${modeChip(L.derived.mode[L.user])}<span class="label">${U.esc(t.arena)}</span></div>
    </section>
    <div class="grid" style="grid-template-columns: 2fr 1fr; margin-bottom:16px">
      ${phaseHero()}
      ${lastResult() || U.slab("Your leaders", top.length ? top.map((x) => `<div class="leader-card"><div class="cat">${U.f1(x.s.pts)} PPG</div>${U.pname(x.p, t, x.p.pos)}<div class="mono dim">${U.f1(x.s.reb)}r ${U.f1(x.s.ast)}a</div></div>`).join("") : `<div class="empty">Season hasn't started</div>`)}
    </div>
    <div class="grid g3">
      ${U.slab("Standings", standingsMini(), { right: `<a class="label acc" href="#/standings">Full →</a>`, flush: false })}
      ${U.slab("League leaders", leadersMini(seasonKey()), { right: `<a class="label acc" href="#/stats">All →</a>` })}
      ${U.slab("Wire", `<div style="max-height:380px;overflow:auto">${newsFeed(18)}</div>`)}
    </div>
    <div class="grid g2" style="margin-top:16px">
      ${lockerRoom()}
      ${U.slab("Your rivalries", rivalryList(L.user, 5), { right: `<a class="label acc" href="#/teams">All →</a>` })}
    </div>`;
}

export function lockerRoom() {
  const L = S.L;
  const ps = roster(L.user).sort((a, b) => (a.morale ?? 65) - (b.morale ?? 65));
  const chem = L.derived.chem[L.user];
  const alerts = ps.filter((p) => p.treq || (p.morale ?? 65) < 40).slice(0, 4);
  const happy = ps.slice().reverse().slice(0, 2);
  return U.slab("Locker room", `<div class="row" style="gap:18px;margin-bottom:12px">
      <div><div class="label">Team chemistry</div><div class="big-num" style="font-size:32px">${chem}</div></div>
      <div class="sp" style="min-width:120px"><div class="chem"><i style="width:${chem}%"></i></div><div class="dim" style="font-size:12px;margin-top:6px">${chem >= 80 ? "Locked in. This group plays for each other." : chem >= 68 ? "Healthy locker room." : chem >= 55 ? "Some grumbling. Watch the minutes." : "Fractured. Players are tuning you out."}</div></div></div>
    ${alerts.length ? alerts.map((p) => `<div class="row" style="padding:6px 0;border-top:1px solid var(--line)">${U.pname(p, me(), `${p.trait || ""} · ${U.moodLabel(p.morale ?? 65)}`)}<span class="sp"></span>${U.moodChip(p)}</div>`).join("") : `<div class="dim" style="font-size:12.5px">No complaints right now.</div>`}
    <div class="label" style="margin:10px 0 4px">Happiest</div>
    ${happy.map((p) => `<div class="row" style="padding:4px 0">${U.pname(p, me(), p.trait || "", false)}<span class="sp"></span>${U.moodChip(p)}</div>`).join("")}
    <div class="dim" style="font-size:11.5px;margin-top:8px">Open a player's card to talk to him. Each personality responds to a different approach.</div>`);
}

ACT["sim-day"] = async () => {
  const r = await act("sim_day", {}, { rerender: false });
  if (r?.user_gid) {
    const res = S.L.results.find((g) => g.gid === r.user_gid);
    if (res) {
      const won = (res.h === S.L.user) === (res.hs > res.as);
      U.toast(`${won ? "WIN" : "LOSS"} · ${T(res.a).abbr} ${res.as} – ${T(res.h).abbr} ${res.hs}${res.ot ? " (OT)" : ""}`);
    }
  }
  render();
};
ACT["watch"] = async () => {
  const r = await act("sim_day", {}, { rerender: false, label: "TIPPING OFF" });
  if (r?.user_gid) go(`#/game/${r.user_gid}?watch=1`); else render();
};
ACT["sim-until"] = async (el) => {
  const r = await act("sim_until", { until: el.dataset.u }, { label: "SIMULATING" });
  if (S.L.phase === "offseason") go("#/playoffs");
};
function render() { hooks.render(); }

// ================================================================== ROSTER
const STRAT = [
  ["pace", "Pace", [["slow", "Slow"], ["normal", "Normal"], ["fast", "Fast"]], "Fewer or more possessions per game. Run fast with depth and athleticism. Slow it down to shorten games against better teams."],
  ["focus", "Offensive focus", [["inside", "Inside"], ["balanced", "Balanced"], ["perimeter", "Perimeter"]], "Shifts your shot mix toward rim and post attempts, or toward threes."],
  ["star", "Star usage", [["share", "Share"], ["normal", "Normal"], ["heliocentric", "Heliocentric"]], "How hard you feed your best player. Heliocentric runs the offense through your top two."],
  ["defense", "Defense", [["conservative", "Contain"], ["normal", "Normal"], ["aggressive", "Gamble"]], "Gambling forces more steals and turnovers, but gives up more fouls and open threes."],
  ["rotation", "Rotation", [["tight", "8-man"], ["standard", "10-man"], ["deep", "11-man"]], "How deep the coach goes into the bench. A tight rotation tires out your starters."],
];
for (const [k] of STRAT) SEG[`strat-${k}`] = (v) => act("set_strategy", { strategy: { [k]: v } }, { label: "SAVING" });

function strategyPanel() {
  const st = me().strategy;
  return U.slab("Coaching strategy", `<div class="strategy">${STRAT.map(([k, lab, opts, hint]) => `<div class="opt"><span style="font-weight:700">${lab}</span>${U.seg(`strat-${k}`, st[k], opts)}<div class="hint">${hint}</div></div>`).join("")}</div>`);
}

const SLOT_NAMES = ["PG", "SG", "SF", "PF", "C"];
function lineupTable() {
  const L = S.L, t = me();
  const depth = { tight: 8, standard: 10, deep: 11 }[t.strategy.rotation];
  const ps = lineupOf(L.user);
  return `<div class="tbl-wrap"><table class="tbl" id="lineup-tbl"><thead><tr><th class="l"></th><th class="l">Role</th><th class="l">Player</th><th class="c">Pos</th><th>Age</th><th class="l">Personality</th><th class="l">Mood</th><th class="c">OVR</th><th class="c">Rating</th><th>PPG</th><th>RPG</th><th>APG</th><th>MIN</th><th class="c"></th></tr></thead><tbody>
    ${ps.map((p, i) => { const s = pg(p); return `<tr class="lineup-row ${i === 4 ? "cutline" : ""} ${i >= depth ? "dim-row" : ""}" draggable="true" data-pid="${p.id}">
      <td class="l"><span class="drag">⠿</span></td>
      <td class="l"><span class="slot-tag">${i < 5 ? "START · " + SLOT_NAMES[i] : i < depth ? "BENCH " + (i - 4) : "RESERVE"}</span></td>
      <td class="l">${U.pname(p, t, `${p.arch} · ${U.ht(p.ht)}`)}</td><td class="c">${U.pos(p.pos)}</td><td>${p.age}</td>
      <td class="l">${U.traitChip(p)}</td><td class="l">${U.moodChip(p)}</td>
      <td class="c">${U.ovrBadge(p)}</td><td class="c">${U.stars(p.stars)}</td>
      <td class="hl">${s ? U.f1(s.pts) : "—"}</td><td>${s ? U.f1(s.reb) : "—"}</td><td>${s ? U.f1(s.ast) : "—"}</td><td>${s ? U.f1(s.min) : "—"}</td>
      <td class="c"><span class="lu-arrows"><button class="iconbtn" data-act="lu-move" data-pid="${p.id}" data-d="-1">▲</button><button class="iconbtn" data-act="lu-move" data-pid="${p.id}" data-d="1">▼</button></span></td></tr>`; }).join("")}
  </tbody></table></div>`;
}

function ratingsTable(ps, team) {
  const A = S.L.consts.attrs;
  const short = { ins: "FIN", mid: "MID", three: "3PT", ft: "FT", post: "PST", pass: "PAS", hand: "HND", iq: "IQ", perd: "PER", intd: "INT", stl: "STL", blk: "BLK", reb: "REB", ath: "ATH", sta: "STA" };
  const col = (v) => (v >= 85 ? "var(--volt)" : v >= 72 ? "var(--txt)" : v >= 55 ? "var(--dim)" : "var(--mute)");
  return `<div class="tbl-wrap"><table class="tbl compact"><thead><tr><th class="l">Player</th><th class="c">Pos</th><th class="c">OVR</th><th class="c">POT</th>${A.map((a) => `<th title="${S.L.consts.attr_label[a]}">${short[a]}</th>`).join("")}</tr></thead><tbody>
    ${ps.map((p) => `<tr><td class="l">${U.pname(p, team || T(p.tid), null, false)}</td><td class="c">${U.pos(p.pos)}</td><td class="c">${U.ovrBadge(p)}</td><td class="c">${U.stars(p.pstars, "pot")}</td>
      ${A.map((a) => `<td style="color:${col(p.a[a])}">${p.a[a]}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

export function statsTable(ps, po = false, showTeam = false) {
  const rows = ps.map((p) => ({ p, s: pg(p, po) })).filter((x) => x.s);
  if (!rows.length) return `<div class="empty">No stats yet</div>`;
  return `<div class="tbl-wrap"><table class="tbl compact"><thead><tr><th class="l">Player</th>${showTeam ? `<th class="l">Tm</th>` : ""}<th>GP</th><th>GS</th><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th><th>STL</th><th>BLK</th><th>TOV</th><th>FG%</th><th>3P%</th><th>FT%</th><th>TS%</th><th>+/-</th></tr></thead><tbody>
    ${rows.sort((a, b) => b.s.pts - a.s.pts).map(({ p, s }) => `<tr><td class="l">${U.pname(p, T(p.tid), null, false)}</td>${showTeam ? `<td class="l">${U.tlink(T(p.tid), 16)}</td>` : ""}<td>${s.gp}</td><td>${s.gs}</td><td>${U.f1(s.min)}</td><td class="hl">${U.f1(s.pts)}</td><td>${U.f1(s.reb)}</td><td>${U.f1(s.ast)}</td><td>${U.f1(s.stl)}</td><td>${U.f1(s.blk)}</td><td>${U.f1(s.tov)}</td><td>${U.pct(s.fgp, 1)}</td><td>${U.pct(s.tpp, 1)}</td><td>${U.pct(s.ftp, 1)}</td><td>${U.pct(s.ts, 1)}</td><td>${U.sign(Math.round(s.pm * 10) / 10)}</td></tr>`).join("")}</tbody></table></div>`;
}

function contractsTable() {
  const L = S.L, t = me();
  const ps = roster(L.user).sort((a, b) => (b.contract?.sal || 0) - (a.contract?.sal || 0));
  const block = new Set(L.block.players);
  return `<div class="tbl-wrap"><table class="tbl"><thead><tr><th class="l">Player</th><th class="c">Pos</th><th>Age</th><th class="c">OVR</th><th>Salary</th><th>Years</th><th>Trade value</th><th class="c">Status</th><th class="c"></th></tr></thead><tbody>
    ${ps.map((p) => `<tr><td class="l">${U.pname(p, t, p.arch)}</td><td class="c">${U.pos(p.pos)}</td><td>${p.age}</td><td class="c">${U.ovrBadge(p)}</td>
      <td class="hl">${p.contract ? U.money(p.contract.sal) : "—"}</td><td>${p.contract ? p.contract.yrs : "—"}</td><td>${p.tv}</td>
      <td class="c">${L.resign.includes(p.id) ? `<span class="chip hot">Expiring</span>` : block.has(p.id) ? `<span class="chip acc">On block</span>` : ""}</td>
      <td class="c"><button class="btn xs ${block.has(p.id) ? "" : "ghost"}" data-act="toggle-block" data-pid="${p.id}">${block.has(p.id) ? "Unblock" : "Block"}</button>
      <button class="btn xs danger" data-act="release" data-pid="${p.id}">Release</button></td></tr>`).join("")}
  </tbody></table></div>
  <div class="row wrap" style="margin-top:14px;gap:22px">
    <div><div class="label">Payroll</div><div class="mono hl">${U.money(L.derived.payroll[L.user])}</div></div>
    <div><div class="label">Cap</div><div class="mono">${U.money(L.consts.cap)}</div></div>
    <div><div class="label">Hard apron</div><div class="mono">${U.money(L.consts.apron)}</div></div>
    <div><div class="label">Dead money</div><div class="mono">${U.money(t.dead || 0)}</div></div>
    <div><div class="label">Mid-level exception</div><div class="mono">${t.mle ? "Used" : U.money(L.consts.mle) + " available"}</div></div>
  </div>`;
}

function rosterView() {
  const L = S.L, tab = S.ui.rosterTab;
  const n = roster(L.user).length;
  const tabs = [["lineup", "Lineup & Rotation"], ["ratings", "Ratings"], ["stats", "Season Stats"], ["contracts", "Contracts"]];
  let body;
  if (tab === "lineup") {
    body = `<div class="grid" style="grid-template-columns: minmax(0,1fr) 380px">
      ${U.slab("Depth chart", `<div class="dim" style="font-size:12px;margin:-4px 0 12px">Drag rows or use the arrows. The top 5 start. Players below the rotation cutoff only play in garbage time or when injuries and fouls force it.</div>${lineupTable()}`, { right: `<button class="btn sm" data-act="auto-lineup">Auto-set</button>` })}
      ${strategyPanel()}</div>`;
  } else if (tab === "ratings") body = U.slab("Attribute ratings", ratingsTable(lineupOf(L.user), me()));
  else if (tab === "stats") body = U.slab(`${L.season} regular season`, statsTable(roster(L.user))) + (roster(L.user).some((p) => p.stats?.[seasonKey(true)]) ? `<div style="height:16px"></div>` + U.slab("Playoffs", statsTable(roster(L.user), true)) : "");
  else body = U.slab("Contracts & trade block", contractsTable());
  return head("Roster", `${U.esc(me().name)}`, `${n}/${L.consts.roster_max} players · team OVR ${L.derived.strength[L.user]}`, "") +
    `<div class="tabs">${tabs.map(([k, l]) => `<button class="${tab === k ? "on" : ""}" data-act="roster-tab" data-t="${k}">${l}</button>`).join("")}</div>` + body;
}
ACT["roster-tab"] = (el) => { S.ui.rosterTab = el.dataset.t; render(); };
ACT["auto-lineup"] = () => act("auto_lineup", {}, { label: "SAVING" });
ACT["lu-move"] = (el) => {
  const ids = lineupOf(S.L.user).map((p) => p.id);
  const i = ids.indexOf(+el.dataset.pid), j = i + +el.dataset.d;
  if (j < 0 || j >= ids.length) return;
  [ids[i], ids[j]] = [ids[j], ids[i]];
  act("set_lineup", { order: ids }, { label: "SAVING" });
};
ACT["toggle-block"] = (el) => {
  const b = S.L.block, pid = +el.dataset.pid;
  const players = b.players.includes(pid) ? b.players.filter((x) => x !== pid) : [...b.players, pid];
  act("block_set", { players, picks: b.picks }, { label: "SAVING" });
};
ACT["release"] = (el) => {
  const p = Pl(el.dataset.pid);
  const dead = p.contract ? (p.contract.sal * (S.L.phase === "offseason" ? 0.25 : 0.5)).toFixed(1) : 0;
  const msg = S.L.resign.includes(p.id) ? `Let ${p.fn} ${p.ln} walk in free agency?` : `Release ${p.fn} ${p.ln}? $${dead}M stays on your books as dead money this season.`;
  if (!confirm(msg)) return;
  act("release", { pid: p.id }).then(() => import("./app.js").then((m) => m.closeModal()));
};
function rosterMount() {
  const tb = document.querySelector("#lineup-tbl tbody");
  if (!tb) return;
  let dragId = null;
  tb.querySelectorAll("tr").forEach((tr) => {
    tr.addEventListener("dragstart", (e) => { dragId = +tr.dataset.pid; tr.classList.add("dragging"); e.dataTransfer.effectAllowed = "move"; });
    tr.addEventListener("dragend", () => tr.classList.remove("dragging"));
    tr.addEventListener("dragover", (e) => { e.preventDefault(); tr.classList.add("drop-above"); });
    tr.addEventListener("dragleave", () => tr.classList.remove("drop-above"));
    tr.addEventListener("drop", (e) => {
      e.preventDefault(); tr.classList.remove("drop-above");
      const ids = lineupOf(S.L.user).map((p) => p.id);
      const target = +tr.dataset.pid;
      if (dragId === null || dragId === target) return;
      ids.splice(ids.indexOf(dragId), 1);
      ids.splice(ids.indexOf(target), 0, dragId);
      act("set_lineup", { order: ids }, { label: "SAVING" });
    });
  });
}

// ================================================================== SCHEDULE
function gameCell(g, res, L) {
  const mine = g.h === L.user || g.a === L.user;
  if (res) {
    const hw = res.hs > res.as;
    return `<div class="asset ${mine ? "on" : ""}" style="grid-template-columns:1fr auto" data-go="#/game/${res.gid}">
      <div class="col" style="gap:4px"><div class="row"><span class="${hw ? "mute" : ""}">${U.tlink(T(g.a), 18)}</span><span class="sp"></span><b class="mono ${hw ? "mute" : ""}">${res.as}</b></div>
      <div class="row"><span class="${hw ? "" : "mute"}">${U.tlink(T(g.h), 18)}</span><span class="sp"></span><b class="mono ${hw ? "" : "mute"}">${res.hs}</b></div></div>
      <span class="label">${res.ot ? "OT" : "F"}</span></div>`;
  }
  return `<div class="asset ${mine ? "on" : ""}" style="grid-template-columns:1fr;cursor:default"><div class="col" style="gap:4px"><div class="row">${U.tlink(T(g.a), 18)}<span class="sp"></span><span class="mono mute">${recordStr(T(g.a))}</span></div><div class="row">${U.tlink(T(g.h), 18)}<span class="sp"></span><span class="mono mute">${recordStr(T(g.h))}</span></div></div></div>`;
}

function schedule() {
  const L = S.L;
  const byGid = Object.fromEntries(L.results.map((r) => [r.gid, r]));
  const days = L.schedule.map((day, d) => U.slab(`Day ${d + 1}${L.phase === "regular" && d === L.day ? " · next" : ""}`, day.map((g, i) => gameCell(g, byGid[`${L.season}-r${d + 1}-${i}`], L)).join(""), { cls: L.phase === "regular" && d === L.day ? "glow" : "" })).join("");
  const po = L.results.filter((r) => r.po);
  const mine = L.results.filter((r) => !r.po && (r.h === L.user || r.a === L.user));
  return head(`${L.season} season`, "Schedule & Results", `${L.consts.days}-game round robin: everyone plays everyone once.`) +
    (mine.length ? U.slab("Your results", `<div class="row wrap" style="gap:8px">${mine.map((r) => { const won = (r.h === L.user) === (r.hs > r.as); const opp = r.h === L.user ? r.a : r.h; return `<span class="chip ${won ? "good" : "bad"}" style="cursor:pointer;padding:6px 10px" data-go="#/game/${r.gid}">${won ? "W" : "L"} ${r.h === L.user ? "vs" : "@"} ${T(opp).abbr} ${Math.max(r.hs, r.as)}-${Math.min(r.hs, r.as)}</span>`; }).join("")}</div>`) + `<div style="height:16px"></div>` : "") +
    `<div class="grid g3">${days}</div>` +
    (po.length ? `<div style="height:16px"></div>` + U.slab("Playoff games", `<div class="grid g4">${po.map((r) => gameCell({ h: r.h, a: r.a }, r, L)).join("")}</div>`) : "");
}

// ================================================================== STANDINGS
function standings() {
  const L = S.L;
  const rows = L.derived.standings.map((tid, i) => {
    const t = T(tid), gp = t.w + t.l, lead = T(L.derived.standings[0]);
    const gb = ((lead.w - t.w) + (t.l - lead.l)) / 2;
    return `<tr class="${tid === L.user ? "me" : ""} ${i === 3 ? "cutline" : ""}"><td class="l mute">${i + 1}</td><td class="l">${U.tlink(t, 24, true)}</td>
      <td class="hl">${t.w}</td><td>${t.l}</td><td>${gp ? U.pct(t.w, gp) : "—"}</td><td>${gb ? gb.toFixed(1) : "—"}</td>
      <td>${gp ? U.f1(t.pf / gp) : "—"}</td><td>${gp ? U.f1(t.pa / gp) : "—"}</td><td class="${t.pf - t.pa >= 0 ? "good" : "bad"}">${U.sign(t.pf - t.pa)}</td><td>${streak(t.streak)}</td>
      <td>${L.derived.strength[tid]}</td><td>${U.money(L.derived.payroll[tid])}</td><td class="c">${modeChip(L.derived.mode[tid])}</td></tr>`;
  }).join("");
  return head(`${L.season} season`, "Standings", "Top 4 make the playoffs. Ties go to head-to-head, then point differential.") +
    U.slab("League table", `<div class="tbl-wrap"><table class="tbl"><thead><tr><th class="l">#</th><th class="l">Team</th><th>W</th><th>L</th><th>PCT</th><th>GB</th><th>PF/G</th><th>PA/G</th><th>DIFF</th><th>STRK</th><th>Team OVR</th><th>Payroll</th><th class="c">Mode</th></tr></thead><tbody>${rows}</tbody></table></div>`);
}

// ================================================================== STATS
const LEADER_CATS = [["Points", "pts"], ["Rebounds", "reb"], ["Assists", "ast"], ["Steals", "stl"], ["Blocks", "blk"], ["FG%", "fgp"], ["3P%", "tpp"], ["True Shooting", "ts"]];
function stats() {
  const L = S.L, po = S.ui.statsPo || false;
  const key = seasonKey(po);
  const all = Object.values(L.players).filter((p) => p.stats?.[key]);
  const rows = all.map((p) => ({ p, s: U.perGame(p.stats[key]) }));
  const minG = po ? 1 : Math.max(1, Math.ceil(L.day * 0.5));
  const cards = LEADER_CATS.map(([lab, k]) => {
    let pool = rows.filter((r) => r.s.gp >= minG);
    if (k === "fgp") pool = pool.filter((r) => r.s.fga >= 6);
    if (k === "tpp") pool = pool.filter((r) => r.s.tpa >= 3);
    if (k === "ts") pool = pool.filter((r) => r.s.fga >= 8);
    const top = pool.sort((a, b) => b.s[k] - a.s[k]).slice(0, 5);
    const fmt = (v) => (["fgp", "tpp", "ts"].includes(k) ? U.pct(v, 1) : U.f1(v));
    return U.slab(lab, top.length ? top.map((r, i) => `<div class="leader-card" style="grid-template-columns:20px 1fr auto"><div class="cat">${i + 1}</div>${U.pname(r.p, T(r.p.tid), `${T(r.p.tid).abbr} · ${r.p.pos}`)}<div class="val" style="font-size:${i ? 15 : 20}px">${fmt(r.s[k])}</div></div>`).join("") : `<div class="empty">—</div>`);
  }).join("");
  const team = S.ui.statsTeam;
  const tsel = `<select id="stats-team">${[["all", "All teams"], ...L.teams.map((t) => [t.tid, t.city + " " + t.name])].map(([v, l]) => `<option value="${v}" ${String(team) === String(v) ? "selected" : ""}>${U.esc(l)}</option>`).join("")}</select>`;
  const list = all.filter((p) => team === "all" || p.stats[key].tid === +team);
  return head(`${L.season} ${po ? "playoffs" : "regular season"}`, "League Stats", "", `${U.seg("stats-po", po ? "po" : "rs", [["rs", "Regular"], ["po", "Playoffs"]])}`) +
    `<div class="grid g4" style="margin-bottom:16px">${cards}</div>` + U.slab("Player stats", statsTable(list, po, true), { right: tsel });
}
SEG["stats-po"] = (v) => { S.ui.statsPo = v === "po"; render(); };
function statsMount() {
  document.getElementById("stats-team")?.addEventListener("change", (e) => { S.ui.statsTeam = e.target.value; render(); });
}

// ================================================================== PLAYOFFS
function seriesBox(s, seeds) {
  if (!s) return `<div class="series"><div class="tm"><span></span><span></span><span class="mute">TBD</span><span></span></div><div class="tm"><span></span><span></span><span class="mute">TBD</span><span></span></div></div>`;
  const line = (tid, w, idx) => `<div class="tm ${s.winner === tid ? "win" : s.winner !== null ? "lose" : ""}"><span class="seed">${seeds.indexOf(tid) + 1}</span>${U.logo(T(tid), 26)}<span>${U.tlink(T(tid), 0)}</span><span class="w">${w}</span></div>`;
  const games = S.L.results.filter((r) => r.series === s.id && r.s === S.L.season);
  return `<div class="series">${line(s.hi, s.w[0])}${line(s.lo, s.w[1])}
    ${games.length ? `<div class="row wrap" style="gap:4px;padding:8px 10px;border-top:1px solid var(--line)">${games.map((g, i) => `<span class="chip" style="cursor:pointer" data-go="#/game/${g.gid}">G${i + 1} ${T(g.hs > g.as ? g.h : g.a).abbr} ${Math.max(g.hs, g.as)}-${Math.min(g.hs, g.as)}</span>`).join("")}</div>` : ""}</div>`;
}

function playoffs() {
  const L = S.L;
  const po = L.playoffs;
  if (!po) {
    const top4 = L.derived.standings.slice(0, 4);
    const last = L.history[L.history.length - 1];
    return head(`${L.season}`, "Playoff Picture", "If the season ended today:") +
      `<div class="grid g2">${U.slab("Projected bracket", `<div class="col">${seriesBox({ id: "x", hi: top4[0], lo: top4[3], w: [0, 0], winner: null }, top4)}${seriesBox({ id: "y", hi: top4[1], lo: top4[2], w: [0, 0], winner: null }, top4)}</div>`)}
      ${last ? U.slab("Defending champion", `<div class="row">${U.logo(T(last.champ), 80)}<div><div class="display" style="font-size:22px;font-weight:800">${U.esc(T(last.champ).city)} ${U.esc(T(last.champ).name)}</div><div class="label">${last.s} champions · beat ${T(last.runner).abbr} ${Math.max(...last.fin)}-${Math.min(...last.fin)}</div></div></div>`) : ""}</div>`;
  }
  const sf = po.series.filter((s) => s.rd === 1), fin = po.series.find((s) => s.rd === 2);
  const champ = po.champion !== null && po.champion !== undefined ? T(po.champion) : null;
  const hist = L.history.find((h) => h.s === L.season);
  return head(`${L.season} postseason`, "Playoffs", "Semifinals and Finals are both best-of-five, in a 2-2-1 format.",
    L.phase === "playoffs" ? `<button class="btn pri" data-act="sim-day">Sim next day</button><button class="btn ghost" data-act="sim-until" data-u="champion">Sim to champion</button>` : L.phase === "offseason" ? `<button class="btn pri" data-go="#/offseason">Go to offseason →</button>` : "") +
    U.slab("Bracket", `<div class="bracket">
      <div class="col" style="gap:30px"><div class="label">Semifinals</div>${seriesBox(sf[0], po.seeds)}${seriesBox(sf[1], po.seeds)}</div>
      <div class="col"><div class="label">Finals</div>${seriesBox(fin, po.seeds)}</div>
      <div class="trophy">${champ ? `<div class="cup">🏆</div>${U.logo(champ, 90)}<div class="display" style="font-size:22px;font-weight:900;margin-top:10px">${U.esc(champ.city)} ${U.esc(champ.name)}</div><div class="label" style="margin-top:6px">${L.season} champions</div>` : `<div class="cup" style="opacity:.25">🏆</div><div class="label">Awaiting a champion</div>`}</div>
    </div>`) + (hist ? `<div style="height:16px"></div>` + awardsSlab(hist) : "");
}

export function awardsSlab(h) {
  const L = S.L;
  const nm = (pid) => {
    const p = Pl(pid);
    if (!p) return `<span>${U.esc(h.names[String(pid)] || "—")}</span>`;
    const tid = p.stats?.[String(h.s)]?.tid ?? p.tid;   // team he played for that season
    return U.pname(p, T(tid), `${T(tid).abbr} · ${p.pos}`);
  };
  const singles = ["MVP", "FMVP", "DPOY", "ROY", "6MOY", "MIP"].filter((k) => h.awards[k] !== undefined);
  return U.slab(`${h.s} awards`, `<div class="grid g3">${singles.map((k) => `<div class="stat-tile"><div class="award-pill">${L.consts.award_names[k]}</div><div style="margin-top:10px">${nm(h.awards[k])}</div></div>`).join("")}</div>
    <div class="grid g2" style="margin-top:16px">${["ALL1", "ALL2"].filter((k) => h.awards[k]).map((k) => `<div><div class="label" style="margin-bottom:8px">${L.consts.award_names[k]}</div><div class="col">${h.awards[k].map(nm).join("")}</div></div>`).join("")}</div>`);
}

// ================================================================== LEAGUE / TEAMS
function teams() {
  const L = S.L;
  return head(`${L.season}`, "League", "All ten franchises. Click any team to see its roster, picks and history.") +
    U.slab("Rivalry board", `<div class="grid g2" style="gap:10px">${rivalryList(null, 10)}</div><div class="dim" style="font-size:12px;margin-top:10px">Rivalries heat up with close games, overtime, blowouts and playoff series, and cool off a little each offseason. Hotter rivalries mean more fouls, louder crowds, bigger momentum swings, bigger mood swings and bonus franchise points.</div>`) +
    `<div style="height:16px"></div><div class="grid g3">${L.derived.standings.map((tid) => {
      const t = T(tid);
      const top = roster(tid).sort((a, b) => b.ovr - a.ovr).slice(0, 3);
      return `<section class="slab ${tid === L.user ? "glow" : ""}" style="cursor:pointer" data-team="${tid}">
        <div class="row">${U.logo(t, 54)}<div><div class="label">${U.esc(t.city)}</div><div class="display" style="font-size:19px;font-weight:800">${U.esc(t.name)}</div></div><div class="sp"></div><div style="text-align:right"><div class="big-num" style="font-size:24px">${recordStr(t)}</div><div class="label">OVR ${L.derived.strength[tid]}</div></div></div>
        <div class="divider"></div>
        <div class="col" style="gap:8px">${top.map((p) => `<div class="row">${U.ovrBadge(p)}<span style="font-weight:600">${U.esc(p.fn[0])}. ${U.esc(p.ln)}</span><span class="mute mono" style="font-size:10px">${p.pos}</span><span class="sp"></span>${U.stars(p.stars)}</div>`).join("")}</div>
        <div class="row" style="margin-top:12px">${modeChip(L.derived.mode[tid])}<span class="sp"></span><span class="label">${U.money(L.derived.payroll[tid])} · ${t.titles || 0}🏆</span></div></section>`;
    }).join("")}</div>`;
}

function teamPage(r) {
  const L = S.L, tid = +r.arg, t = L.teams[tid];
  if (!t) return teams();
  const ps = lineupOf(tid);
  const picks = L.picks.filter((pk) => pk.owner === tid);
  return `<section class="slab hero" style="margin-bottom:16px;--cut:22px;--acc2:${t.c2}">
      ${U.logo(t, 110)}
      <div><div class="hero-name" style="color:${t.c1}"><span class="city">${U.esc(t.city)}</span>${U.esc(t.name)}</div>
      <div class="hero-stats"><div><div class="label">Record</div><div class="v">${recordStr(t)}</div></div><div><div class="label">Team OVR</div><div class="v">${L.derived.strength[tid]}</div></div><div><div class="label">Payroll</div><div class="v">${U.money(L.derived.payroll[tid])}</div></div><div><div class="label">Titles</div><div class="v">${t.titles || 0}</div></div></div></div>
      <div class="col" style="align-items:flex-end">${modeChip(L.derived.mode[tid])}${tid !== L.user ? `<button class="btn pri" data-act="trade-with" data-tid="${tid}">Trade with ${U.esc(t.abbr)}</button>` : ""}<span class="label">${U.esc(t.arena)}</span></div>
    </section>
    <div class="grid" style="grid-template-columns:minmax(0,1fr) 320px">
      <div class="col" style="gap:16px">
        ${U.slab("Roster", `<div class="tbl-wrap"><table class="tbl"><thead><tr><th class="l">Player</th><th class="c">Pos</th><th>Age</th><th class="c">OVR</th><th class="c">Rating</th><th class="c">Potential</th><th>Salary</th><th>Yrs</th><th>PPG</th></tr></thead><tbody>
          ${ps.map((p, i) => { const s = pg(p); return `<tr class="${i === 4 ? "cutline" : ""}"><td class="l">${U.pname(p, t, p.arch)}</td><td class="c">${U.pos(p.pos)}</td><td>${p.age}</td><td class="c">${U.ovrBadge(p)}</td><td class="c">${U.stars(p.stars)}</td><td class="c">${U.stars(p.pstars, "pot")}</td><td>${p.contract ? U.money(p.contract.sal) : "—"}</td><td>${p.contract?.yrs ?? "—"}</td><td class="hl">${s ? U.f1(s.pts) : "—"}</td></tr>`; }).join("")}</tbody></table></div>`)}
        ${U.slab("Season stats", statsTable(ps))}
      </div>
      <div class="col" style="gap:16px">
        ${U.slab("Strategy", `<div class="col">${Object.entries(t.strategy).map(([k, v]) => `<div class="row"><span class="label">${k}</span><span class="sp"></span><span class="chip">${v}</span></div>`).join("")}</div>`)}
        ${U.slab("Draft picks owned", picks.length ? picks.map((pk) => `<div class="row" style="padding:6px 0;border-bottom:1px solid var(--line)"><span class="mono">${U.esc(pk.label)}</span><span class="sp"></span><span class="label">val ${pk.tv}</span></div>`).join("") : `<div class="empty">No picks</div>`)}
        ${U.slab("Rivals", rivalryList(tid, 4))}
        ${U.slab("Facilities", `<div class="row"><span class="label">Chemistry</span><span class="sp"></span><b class="mono">${L.derived.chem[tid]}</b></div>${L.consts.tracks.map((tr) => `<div class="row" style="padding:3px 0"><span style="font-size:12px">${U.esc(tr.name)}</span><span class="sp"></span>${U.pips(t.upg?.[tr.key] || 0)}</div>`).join("")}`)}
        ${U.slab("Franchise history", t.hist.length ? t.hist.slice().reverse().map((h) => `<div class="row" style="padding:6px 0;border-bottom:1px solid var(--line)"><span class="mono">${h.s}</span><span class="mono hl">${h.w}-${h.l}</span><span class="sp"></span><span class="chip ${h.res === "Champion" ? "volt" : h.res === "Finals" ? "acc" : ""}">${h.res}</span></div>`).join("") : `<div class="empty">First season</div>`)}
      </div>
    </div>`;
}
ACT["trade-with"] = (el) => { S.ui.tradeTid = +el.dataset.tid; S.ui.give = { players: [], picks: [] }; S.ui.get = { players: [], picks: [] }; S.ui.tradeEval = null; S.ui.tradeTab = "build"; go("#/trade"); };

// ================================================================== HISTORY
function history() {
  const L = S.L;
  const hist = L.history.slice().reverse();
  const titles = L.teams.slice().sort((a, b) => (b.titles || 0) - (a.titles || 0)).filter((t) => t.titles);
  const legends = L.retired.filter((r) => r.peak >= 70 || r.awards.length).sort((a, b) => b.peak - a.peak).slice(0, 12);
  return head("Archive", "League History", `${L.history.length} season${L.history.length === 1 ? "" : "s"} completed`) +
    `<div class="grid" style="grid-template-columns:minmax(0,1fr) 340px">
      <div class="col" style="gap:16px">
      ${U.slab("Champions", hist.length ? hist.map((h) => `<div class="history-row"><div class="big-num" style="font-size:22px">${h.s}</div>
        <div class="row">${U.logo(T(h.champ), 40)}<div><div style="font-weight:800">${U.esc(T(h.champ).city)} ${U.esc(T(h.champ).name)}</div><div class="label">def. ${T(h.runner).abbr} ${Math.max(...h.fin)}-${Math.min(...h.fin)}</div></div></div>
        <div><div class="label">MVP</div><div style="font-weight:600">${U.esc(h.names[String(h.awards.MVP)] || "—")}</div></div>
        <div><div class="label">Your season</div><div class="mono">${h.user.w}-${h.user.l} · ${h.user.res}</div></div></div>`).join("") : `<div class="empty">No completed seasons yet</div>`)}
      ${hist.map((h) => awardsSlab(h)).join("")}
      </div>
      <div class="col" style="gap:16px">
        ${U.slab("Title count", titles.length ? titles.map((t) => `<div class="row" style="padding:8px 0;border-bottom:1px solid var(--line)">${U.tlink(t, 26, true)}<span class="sp"></span><span class="big-num" style="font-size:20px">${t.titles}</span></div>`).join("") : `<div class="empty">No champions yet</div>`)}
        ${U.slab("Retired legends", legends.length ? legends.map((r) => `<div style="padding:8px 0;border-bottom:1px solid var(--line)"><div class="row"><b>${U.esc(r.name)}</b><span class="pos">${r.pos}</span><span class="sp"></span><span class="mono acc">${r.peak}</span></div><div class="label" style="margin-top:4px">${r.career.gp || 0} GP · ${((r.career.pts || 0) / Math.max(1, r.career.gp || 1)).toFixed(1)} PPG${(() => { const c = r.awards.filter((a) => a.a === "CHAMP").length, m = r.awards.filter((a) => a.a === "MVP").length; return (c ? ` · ${c}🏆` : "") + (m ? ` · ${m}× MVP` : ""); })()} · retired ${r.s}</div></div>`).join("") : `<div class="empty">Nobody has retired yet</div>`)}
      </div></div>`;
}

export const VIEWS = {
  hub, roster: rosterView, roster_mount: rosterMount, schedule, standings, stats, stats_mount: statsMount,
  playoffs, teams, team: teamPage, history,
};
