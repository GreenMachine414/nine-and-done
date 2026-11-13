// Front-office pages: draft room, trade center + trade block, free agency, offseason HQ.
import * as U from "./ui.js";
import { S, ACT, SEG, act, sync, query, hooks, T, Pl, me, roster } from "./state.js";
import { awardsSlab } from "./views.js";

const render = () => hooks.render();
const head = (kicker, title, sub = "", right = "") => `<div class="view-head"><div><div class="kicker">${kicker}</div><h1>${title}</h1>${sub ? `<div class="sub">${sub}</div>` : ""}</div><div class="right">${right}</div></div>`;
const SHORT = { ins: "FIN", mid: "MID", three: "3PT", ft: "FT", post: "PST", pass: "PAS", hand: "HND", iq: "IQ", perd: "PER-D", intd: "INT-D", stl: "STL", blk: "BLK", reb: "REB", ath: "ATH" };
const shortAttrs = (p, n = 2) => Object.entries(p.a).filter(([k]) => k !== "sta").sort((a, b) => b[1] - a[1]).slice(0, n).map(([k, v]) => `<span class="chip">${SHORT[k]} ${v}</span>`).join(" ");
const topAttrs = (p, n = 3) => Object.entries(p.a).filter(([k]) => k !== "sta").sort((a, b) => b[1] - a[1]).slice(0, n).map(([k, v]) => `<span class="chip">${S.L.consts.attr_label[k]} ${v}</span>`).join(" ");

// ================================================================== DRAFT
function prospectsTable(pool, canPick, fantasy) {
  const sort = S.ui.draftSort;
  const posF = S.ui.draftPos || "ALL";
  let list = pool.filter((p) => posF === "ALL" || p.pos === posF);
  const key = { rank: (p) => -(fantasy ? p.tv : p.ovr * 0.45 + (p.scout ? (p.scout[0] + p.scout[1]) / 2 : p.pot) * 0.55), ovr: (p) => -p.ovr, pot: (p) => -(p.scout ? p.scout[1] : p.pot), age: (p) => p.age }[sort] || ((p) => -p.ovr);
  list = list.sort((a, b) => key(a) - key(b));
  const th = (k, l) => `<th class="sortable ${sort === k ? "sorted" : ""}" data-act="draft-sort" data-k="${k}">${l}</th>`;
  return `<div class="row wrap" style="margin-bottom:12px">${U.seg("draft-pos", posF, [["ALL", "All"], ["PG", "PG"], ["SG", "SG"], ["SF", "SF"], ["PF", "PF"], ["C", "C"]])}<span class="sp"></span><span class="label">${list.length} available</span></div>
  <div class="tbl-wrap" style="max-height:640px;overflow:auto"><table class="tbl"><thead><tr>${th("rank", "#")}${canPick ? "<th></th>" : ""}<th class="l">Prospect</th><th class="c">Pos</th>${th("age", "Age")}${th("ovr", "OVR")}<th class="c">Now</th>${th("pot", fantasy ? "POT" : "Scout POT")}<th class="l">Best skills</th>${fantasy ? "<th>Salary</th>" : ""}</tr></thead><tbody>
    ${list.slice(0, 120).map((p, i) => `<tr><td class="mute">${i + 1}</td>${canPick ? `<td><button class="btn xs pri" data-act="draft-pick" data-pid="${p.id}">Draft</button></td>` : ""}<td class="l">${U.pname(p, null, fantasy && p.contract ? `${p.arch}` : `${U.esc(p.school)} · ${p.arch}`)}</td><td class="c">${U.pos(p.pos)}</td><td>${p.age}</td>
      <td>${U.ovrBadge(p)}</td><td class="c">${U.stars(p.stars)}</td>
      <td class="hl">${p.scout && !fantasy ? `${p.scout[0]}–${p.scout[1]}` : p.pot}</td>
      <td class="l">${p.tags.length ? p.tags.slice(0, 1).map((t) => `<span class="chip volt">${t}</span>`).join(" ") + " " + shortAttrs(p, 1) : shortAttrs(p, 2)}</td>
      ${fantasy ? `<td>${p.contract ? U.money(p.contract.sal) : "rookie"}</td>` : ""}</tr>`).join("")}
  </tbody></table></div>`;
}
ACT["draft-sort"] = (el) => { S.ui.draftSort = el.dataset.k; render(); };
SEG["draft-pos"] = (v) => { S.ui.draftPos = v; render(); };

function orderStrip(order, cur) {
  const L = S.L;
  const start = Math.max(0, (cur ?? 0) - 3);
  return `<div class="order-strip">${order.slice(start, start + 40).map((o) => {
    const p = o.pid ? Pl(o.pid) : null;
    return `<div class="order-cell ${o.no - 1 === cur ? "cur" : ""} ${o.tid === L.user ? "mine" : ""} ${o.pid ? "done" : ""}" ${o.pid ? `data-player="${o.pid}"` : ""}>
      <span class="no">#${o.no}${o.orig !== o.tid ? ` <span title="via ${T(o.orig).abbr}">*</span>` : ""}</span>${U.logo(T(o.tid), 26)}<span class="who">${p ? U.esc(p.ln) : T(o.tid).abbr}</span></div>`;
  }).join("")}</div>`;
}

function draft() {
  const L = S.L;
  if (L.phase !== "draft") {
    const next = Object.values(L.players).filter((p) => p.tid === -2 && p.dclass === L.season + 1);
    const log = L.derived.draft_log;
    return head("Scouting department", "Draft Room", `The ${L.season + 1} class gets drafted at the start of next season. Scouting ranges tighten as players age.`) +
      (log ? U.slab(`${L.derived.draft_log_season} draft results`, orderStrip(log, null)) + `<div style="height:16px"></div>` : "") +
      U.slab(`${L.season + 1} big board · ${next.length} prospects`, prospectsTable(next, false, false));
  }
  const d = L.draft, oc = L.derived.on_clock, slot = d.order[d.cur], mine = oc === L.user;
  const fantasy = d.type === "fantasy";
  const myNext = d.order.slice(d.cur).find((o) => o.tid === L.user);
  const pool = Object.values(L.players).filter((p) => p.tid === -2 && p.dclass === d.season);
  const myTeam = roster(L.user).sort((a, b) => b.ovr - a.ovr);
  const lottery = d.lottery ? U.slab("Lottery results", `<div class="col">${d.lottery.slice().sort((a, b) => a.pick - b.pick).map((x) => `<div class="row"><span class="mono acc" style="width:30px">#${x.pick}</span>${U.tlink(T(x.tid), 22, true)}<span class="sp"></span><span class="label">seed ${x.seed} · ${x.odds}%</span>${x.pick < x.seed ? `<span class="chip good">▲${x.seed - x.pick}</span>` : x.pick > x.seed ? `<span class="chip bad">▼${x.pick - x.seed}</span>` : ""}</div>`).join("")}</div>`) : "";
  return head(fantasy ? "Fantasy draft · 13 rounds · snake" : `${d.season} rookie draft · 2 rounds`, "Draft Room", fantasy ? "Every player in the league is available. Build a contender from scratch." : "Scouting ranges are estimates. The real potential shows up once a player starts developing.",
    `${mine ? `<button class="btn" data-act="draft-auto">Auto-pick for me</button>` : `<button class="btn pri" data-act="draft-sim" data-to="user">Sim to my pick</button>`}<button class="btn ghost" data-act="draft-sim" data-to="end">Sim entire draft</button>`) +
    `<section class="slab glow clock-banner" style="margin-bottom:16px"><div class="pickno">#${slot.no}</div>${U.logo(T(oc), 60)}
      <div><div class="label">${mine ? "You're on the clock" : "On the clock"} · Round ${slot.rd}</div><div class="display" style="font-size:22px;font-weight:800">${U.esc(T(oc).city)} ${U.esc(T(oc).name)}</div></div>
      <div class="sp"></div><div style="text-align:right"><div class="label">Your next pick</div><div class="big-num" style="font-size:26px">${myNext ? "#" + myNext.no : "—"}</div></div></section>
    ${U.slab("Draft order", orderStrip(d.order, d.cur))}<div style="height:16px"></div>
    <div class="grid" style="grid-template-columns:minmax(0,1fr) 320px">
      ${U.slab(fantasy ? "Player pool" : "Prospects", prospectsTable(pool, mine, fantasy))}
      <div class="col" style="gap:16px">${lottery}
        ${U.slab(`Your roster · ${myTeam.length}`, myTeam.length ? myTeam.map((p) => `<div class="row" style="padding:5px 0">${U.ovrBadge(p)}${U.pname(p, me(), p.pos, false)}</div>`).join("") : `<div class="empty">Empty — start picking</div>`)}
      </div></div>`;
}
ACT["draft-pick"] = (el) => act("draft_pick", { pid: +el.dataset.pid }, { label: "SUBMITTING PICK" }).then(afterDraft);
ACT["draft-auto"] = () => act("draft_auto_pick", {}, { label: "SUBMITTING PICK" }).then(afterDraft);
ACT["draft-sim"] = (el) => act("draft_sim", { to: el.dataset.to }, { label: "DRAFTING" }).then(afterDraft);
function afterDraft() {
  if (S.L.phase === "regular") {
    U.toast("Draft complete. Set your lineup and get ready for the season.");
    location.hash = "#/roster";
  }
}

// ================================================================== TRADE
function assetList(tid, sel, side) {
  const L = S.L;
  const ps = roster(tid).sort((a, b) => b.ovr - a.ovr);
  const picks = L.picks.filter((pk) => pk.owner === tid).sort((a, b) => a.season - b.season || a.rd - b.rd);
  return ps.map((p) => {
    const on = sel.players.includes(p.id);
    const locked = L.resign.includes(p.id);
    return `<div class="asset ${on ? "on" : ""}" ${locked ? "" : `data-act="trade-toggle" data-side="${side}" data-kind="players" data-id="${p.id}"`} style="${locked ? "opacity:.4" : ""}">
      <span class="ck">${on ? "✓" : ""}</span>
      <div class="row" style="gap:8px;min-width:0">${U.ovrBadge(p)}<div style="min-width:0"><div style="font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><span data-player="${p.id}">${U.esc(p.fn[0])}. ${U.esc(p.ln)}</span>${U.injTag(p)}</div><div class="label">${p.pos} · ${p.age}y · ${p.contract ? U.money(p.contract.sal) + " × " + p.contract.yrs : "—"}</div></div></div>
      <div style="text-align:right">${U.stars(p.stars)}<div class="label">val ${p.tv}</div></div></div>`;
  }).join("") + `<div class="label" style="margin:14px 0 8px">Draft picks</div>` + (picks.length ? picks.map((pk) => {
    const on = sel.picks.includes(pk.id);
    return `<div class="asset ${on ? "on" : ""}" data-act="trade-toggle" data-side="${side}" data-kind="picks" data-id="${pk.id}"><span class="ck">${on ? "✓" : ""}</span><div><div style="font-weight:700" class="mono">${U.esc(pk.label)}</div><div class="label">${pk.rd === 1 ? "First round" : "Second round"}</div></div><div class="label">val ${pk.tv}</div></div>`;
  }).join("") : `<div class="empty">No picks</div>`);
}

function tradeSummary() {
  const L = S.L, tid = S.ui.tradeTid, ev = S.ui.tradeEval;
  const give = S.ui.give, get = S.ui.get;
  const sal = (ids) => ids.reduce((a, i) => a + (Pl(i)?.contract?.sal || 0), 0);
  const out = sal(give.players), inn = sal(get.players);
  const after = L.derived.payroll[L.user] - out + inn;
  const names = (sel) => [...sel.players.map((i) => Pl(i) ? `${Pl(i).fn[0]}. ${Pl(i).ln}` : "?"), ...sel.picks.map((id) => L.picks.find((p) => p.id === id)?.label || id)];
  const meter = ev ? Math.min(1, ev.meter / 1.5) : 0;
  const color = ev?.accept ? "var(--good)" : ev && ev.meter > 0.85 ? "var(--warn)" : "var(--bad)";
  return `<div class="col" style="gap:14px">
    <div><div class="label">You send</div><div style="margin-top:6px;font-weight:600">${names(give).join(", ") || `<span class="mute">—</span>`}</div></div>
    <div><div class="label">You receive</div><div style="margin-top:6px;font-weight:600">${names(get).join(", ") || `<span class="mute">—</span>`}</div></div>
    <div class="divider" style="margin:0"></div>
    <div class="grid g3" style="gap:8px"><div><div class="label">Out</div><div class="mono">${U.money(out)}</div></div><div><div class="label">In</div><div class="mono">${U.money(inn)}</div></div><div><div class="label">Payroll after</div><div class="mono ${after > L.consts.cap ? "warn" : ""}">${U.money(after)}</div></div></div>
    <div><div class="row"><span class="label">${U.esc(T(tid).abbr)} front office</span><span class="sp"></span>${ev ? `<span class="chip">${ev.mode}</span>` : ""}</div>
      <div class="meter" style="margin-top:8px"><i style="width:${meter * 100}%;background:${color}"></i><span class="mark"></span></div>
      <div style="margin-top:10px;font-weight:600;color:${ev && !ev.pending ? color : "var(--dim)"}">${ev?.pending ? "Their front office is thinking…" : ev ? U.esc(ev.msg) : "Select assets to get a read from their front office."}</div>
      ${ev?.ask ? `<div class="dim" style="margin-top:6px;font-size:12px">They'd probably do it if you add <b class="acc" style="cursor:pointer" data-act="trade-add-ask" data-kind="${ev.ask.type === "player" ? "players" : "picks"}" data-id="${ev.ask.id}">${U.esc(ev.ask.label)}</b>.</div>` : ""}
    </div>
    <button class="btn pri lg" data-act="trade-propose" ${ev && !ev.pending && !ev.problems?.length ? "" : "disabled"}>Propose trade</button>
    <button class="btn ghost sm" data-act="trade-clear">Clear</button>
  </div>`;
}

function trade() {
  const L = S.L;
  if (!L.derived.trades_open) {
    return head("Front office", "Trade Center") + U.slab("Trades closed", `<div class="empty" style="font-size:13px">${U.esc(L.derived.trades_why)}</div>`);
  }
  const tab = S.ui.tradeTab;
  const tabs = `<div class="tabs"><button class="${tab === "build" ? "on" : ""}" data-act="trade-tab" data-t="build">Build a trade</button><button class="${tab === "block" ? "on" : ""}" data-act="trade-tab" data-t="block">Trade block${L.block.players.length + L.block.picks.length ? ` (${L.block.players.length + L.block.picks.length})` : ""}</button></div>`;
  const dl = L.phase === "regular" ? `Deadline: after game ${L.consts.deadline}${L.day < L.consts.deadline ? ` · ${L.consts.deadline - L.day} game${L.consts.deadline - L.day > 1 ? "s" : ""} left.` : "."}` : "Trades are open.";
  const intro = head("Front office", "Trade Center", `${dl} Over the cap, incoming salary can be at most 125% of outgoing.`);
  if (tab === "block") return intro + tabs + tradeBlock();
  const others = L.teams.filter((t) => t.tid !== L.user);
  if (S.ui.tradeTid === null || S.ui.tradeTid === L.user) S.ui.tradeTid = others[0].tid;
  const tid = S.ui.tradeTid;
  const picker = `<div class="row wrap" style="gap:6px;margin-bottom:16px">${others.map((t) => `<div class="team-tile ${t.tid === tid ? "on" : ""}" style="--tc:${t.c1};padding:8px 10px;flex-direction:row" data-act="trade-team" data-tid="${t.tid}">${U.logo(t, 26)}<div style="text-align:left"><div class="nm">${U.esc(t.abbr)}</div><div class="ct">${t.w}-${t.l} · ${L.derived.mode[t.tid]}</div></div></div>`).join("")}</div>`;
  return intro + tabs + picker + `<div class="trade-grid">
    ${U.slab(`Your assets · ${U.esc(me().abbr)}`, assetList(L.user, S.ui.give, "give"))}
    <div class="trade-mid">${U.slab("Deal sheet", tradeSummary(), { cls: "glow" })}</div>
    ${U.slab(`${U.esc(T(tid).city)} ${U.esc(T(tid).name)} · ${U.money(L.derived.payroll[tid])}`, assetList(tid, S.ui.get, "get"))}
  </div>`;
}

function tradeBlock() {
  const L = S.L;
  const blockSet = new Set(L.block.players), pickSet = new Set(L.block.picks);
  const mine = roster(L.user).sort((a, b) => b.ovr - a.ovr);
  const picks = L.picks.filter((pk) => pk.owner === L.user);
  const offers = L.offers || [];
  const assetsHtml = (o) => [...o.get.players.map((i) => { const p = Pl(i); return p ? `<div class="row" style="padding:4px 0">${U.ovrBadge(p)}${U.pname(p, T(p.tid), `${p.pos} · ${p.age}y · ${p.contract ? U.money(p.contract.sal) + "×" + p.contract.yrs : ""}`, false)}</div>` : ""; }), ...o.get.picks.map((id) => `<div class="mono" style="padding:4px 0">◆ ${U.esc(L.picks.find((p) => p.id === id)?.label || id)}</div>`)].join("");
  return `<div class="grid" style="grid-template-columns:380px minmax(0,1fr)">
    ${U.slab("Shop these assets", `<div class="dim" style="font-size:12px;margin-bottom:10px">Pick what you're willing to move, then ask the league for offers.</div>
      ${mine.map((p) => `<div class="asset ${blockSet.has(p.id) ? "on" : ""}" data-act="block-toggle" data-kind="players" data-id="${p.id}"><span class="ck">${blockSet.has(p.id) ? "✓" : ""}</span><div class="row" style="gap:8px">${U.ovrBadge(p)}<div><div style="font-weight:700">${U.esc(p.fn[0])}. ${U.esc(p.ln)}</div><div class="label">${p.pos} · ${p.age}y</div></div></div><div class="label">val ${p.tv}</div></div>`).join("")}
      <div class="label" style="margin:12px 0 8px">Picks</div>
      ${picks.map((pk) => `<div class="asset ${pickSet.has(pk.id) ? "on" : ""}" data-act="block-toggle" data-kind="picks" data-id="${pk.id}"><span class="ck">${pickSet.has(pk.id) ? "✓" : ""}</span><div class="mono">${U.esc(pk.label)}</div><div class="label">val ${pk.tv}</div></div>`).join("")}
      <button class="btn pri lg" style="width:100%;margin-top:12px" data-act="block-offers" ${blockSet.size + pickSet.size ? "" : "disabled"}>Get offers</button>`)}
    ${U.slab("Incoming offers", offers.length ? offers.map((o) => `<div class="offer">
        <div class="row">${U.tlink(T(o.tid), 30, true)}<span class="sp"></span><span class="chip ${o.value_to_you >= o.value_out ? "good" : "hot"}">value ${o.value_to_you} for ${o.value_out}</span></div>
        <div class="grid g2"><div><div class="label" style="margin-bottom:6px">They send</div>${assetsHtml(o)}</div>
        <div><div class="label" style="margin-bottom:6px">For</div>${[...o.give.players.map((i) => Pl(i) ? `${Pl(i).fn[0]}. ${Pl(i).ln}` : ""), ...o.give.picks.map((id) => L.picks.find((p) => p.id === id)?.label || id)].map((x) => `<div style="padding:4px 0;font-weight:600">${U.esc(x)}</div>`).join("")}</div></div>
        <div class="row"><span class="sp"></span><button class="btn pri sm" data-act="offer-accept" data-id="${o.id}">Accept</button></div></div>`).join("") : `<div class="empty">No offers yet. Put players or picks on the block and hit "Get offers".</div>`)}
  </div>`;
}

// Selections render instantly; the AI's verdict is fetched in the background (debounced, stale replies dropped).
let evalSeq = 0, evalTimer = null;
function evalTrade() {
  const g = S.ui.give, r = S.ui.get;
  clearTimeout(evalTimer);
  if (!g.players.length && !g.picks.length && !r.players.length && !r.picks.length) { S.ui.tradeEval = null; render(); return; }
  S.ui.tradeEval = { ...(S.ui.tradeEval || { meter: 0 }), pending: true };
  render();
  const seq = ++evalSeq;
  evalTimer = setTimeout(async () => {
    let ev;
    try { ev = (await query("trade_eval", { tid: S.ui.tradeTid, give: g, get: r })).eval; }
    catch (e) { ev = { msg: e.message, meter: 0, problems: [e.message] }; }
    if (seq !== evalSeq) return;   // a newer selection superseded this one
    S.ui.tradeEval = ev;
    render();
  }, 160);
}
ACT["trade-tab"] = (el) => { S.ui.tradeTab = el.dataset.t; render(); };
ACT["trade-team"] = (el) => { S.ui.tradeTid = +el.dataset.tid; S.ui.get = { players: [], picks: [] }; evalTrade(); };
ACT["trade-toggle"] = (el, e) => {
  if (e.target.closest("[data-player]")) return;
  const sel = el.dataset.side === "give" ? S.ui.give : S.ui.get;
  const k = el.dataset.kind, id = k === "players" ? +el.dataset.id : el.dataset.id;
  sel[k] = sel[k].includes(id) ? sel[k].filter((x) => x !== id) : [...sel[k], id];
  evalTrade();
};
ACT["trade-add-ask"] = (el) => {
  const k = el.dataset.kind, id = k === "players" ? +el.dataset.id : el.dataset.id;
  if (!S.ui.give[k].includes(id)) S.ui.give[k].push(id);
  evalTrade();
};
ACT["trade-clear"] = () => { S.ui.give = { players: [], picks: [] }; S.ui.get = { players: [], picks: [] }; S.ui.tradeEval = null; render(); };
ACT["trade-propose"] = async () => {
  const res = await act("trade_propose", { tid: S.ui.tradeTid, give: S.ui.give, get: S.ui.get }, { rerender: false });
  if (res.eval.accept) {
    U.toast("Trade accepted!");
    S.ui.give = { players: [], picks: [] }; S.ui.get = { players: [], picks: [] }; S.ui.tradeEval = null;
  } else {
    S.ui.tradeEval = res.eval;
    U.toast("Trade rejected: " + res.eval.msg, true);
  }
  render();
};
ACT["block-toggle"] = (el) => {
  const b = { players: [...S.L.block.players], picks: [...S.L.block.picks] };
  const k = el.dataset.kind, id = k === "players" ? +el.dataset.id : el.dataset.id;
  b[k] = b[k].includes(id) ? b[k].filter((x) => x !== id) : [...b[k], id];
  S.L.block = b;                     // instant
  S.L.offers = [];
  render();
  sync("block_set", b);
};
ACT["block-offers"] = async () => {
  const r = await act("block_offers", {}, { label: "CALLING AROUND THE LEAGUE" });
  if (!r.offers.length) U.toast("No team made an offer. Try putting more on the block.", true);
};
ACT["offer-accept"] = async (el) => { await act("offer_accept", { id: el.dataset.id }); U.toast("Trade complete!"); };

// ================================================================== FREE AGENCY
function fa() {
  const L = S.L, t = me();
  const pay = L.derived.payroll[L.user], room = L.consts.cap - pay;
  const sort = S.ui.faSort;
  const fas = Object.values(L.players).filter((p) => p.tid === -1).sort((a, b) => sort === "ask" ? b.ask.sal - a.ask.sal : sort === "age" ? a.age - b.age : sort === "pot" ? b.pot - a.pot : b.ovr - a.ovr);
  const n = roster(L.user).length;
  const afford = (sal) => pay + sal <= L.consts.apron && (pay + sal <= L.consts.cap || sal <= 1.6 || (!t.mle && sal <= L.consts.mle));
  const th = (k, l) => `<th class="sortable ${sort === k ? "sorted" : ""}" data-act="fa-sort" data-k="${k}">${l}</th>`;
  return head("Front office", "Free Agency", L.phase === "playoffs" ? "Free agency is closed during the playoffs." : "Players ask for less from winning teams. If you're over the cap, you can still sign minimum deals or use your mid-level exception once.") +
    `<div class="grid g4" style="margin-bottom:16px">
      <div class="stat-tile"><div class="label">Payroll</div><div class="v">${U.money(pay)}</div></div>
      <div class="stat-tile"><div class="label">Cap room</div><div class="v ${room < 0 ? "bad" : "good"}">${U.money(room)}</div></div>
      <div class="stat-tile"><div class="label">Mid-level exception</div><div class="v">${t.mle ? "Used" : U.money(L.consts.mle)}</div></div>
      <div class="stat-tile"><div class="label">Roster</div><div class="v">${n} / ${L.consts.roster_max}</div></div></div>` +
    U.slab(`Available · ${fas.length}`, `<div class="tbl-wrap"><table class="tbl"><thead><tr><th class="l">Player</th><th class="c">Pos</th>${th("age", "Age")}${th("ovr", "OVR")}<th class="c">Rating</th>${th("pot", "POT")}<th class="l">Strengths</th>${th("ask", "Asking")}<th>Years</th><th></th></tr></thead><tbody>
      ${fas.map((p) => { const ok = afford(p.ask.sal); return `<tr class="${ok ? "" : "dim-row"}"><td class="l">${U.pname(p, null, p.arch)}</td><td class="c">${U.pos(p.pos)}</td><td>${p.age}</td><td>${U.ovrBadge(p)}</td><td class="c">${U.stars(p.stars)}</td><td class="c">${U.stars(p.pstars, "pot")}</td>
        <td class="l">${p.tags.slice(0, 2).map((x) => `<span class="chip volt">${x}</span>`).join(" ") || topAttrs(p, 2)}</td>
        <td class="hl">${U.money(p.ask.sal)}</td><td><select data-yrs="${p.id}" style="height:26px;padding:0 6px">${[1, 2, 3, 4, 5].map((y) => `<option ${y === p.ask.yrs ? "selected" : ""}>${y}</option>`).join("")}</select></td>
        <td><button class="btn xs ${ok ? "pri" : ""}" data-act="sign" data-pid="${p.id}" ${L.phase === "playoffs" || n >= L.consts.roster_max ? "disabled" : ""}>Sign</button></td></tr>`; }).join("")}
    </tbody></table></div>`);
}
ACT["fa-sort"] = (el) => { S.ui.faSort = el.dataset.k; render(); };
ACT["sign"] = async (el) => {
  const pid = el.dataset.pid;
  const yrs = document.querySelector(`select[data-yrs="${pid}"]`)?.value;
  await act("sign", { pid: +pid, yrs: +yrs }, { label: "NEGOTIATING" });
  U.toast("Signed!");
};

// ================================================================== OFFSEASON
function offseason() {
  const L = S.L;
  if (L.phase !== "offseason") return head("Offseason", "Not yet") + `<div class="empty">The offseason starts after the Finals.</div>`;
  const h = L.history[L.history.length - 1];
  const rep = (L.offseason?.report || []).map((r) => ({ ...r, p: Pl(r.id) })).filter((r) => r.p).sort((a, b) => (b.after - b.before) - (a.after - a.before));
  const retired = (L.offseason?.retired || []).map((id) => L.retired.find((r) => r.id === id)).filter(Boolean).sort((a, b) => b.peak - a.peak);
  const resign = L.resign.map(Pl).filter(Boolean);
  const n = roster(L.user).length - resign.length;
  return head(`${L.season} → ${L.season + 1}`, "Offseason HQ", "Players aged a year: the young ones developed and the veterans slowed down. Lock in your core before free agency opens to everyone.",
    `<button class="btn pri lg" data-act="advance">Advance to ${L.season + 1} draft →</button>`) +
    `<section class="slab hero" style="margin-bottom:16px">${U.logo(T(h.champ), 96)}<div><div class="kicker">${h.s} champions</div><div class="hero-name" style="font-size:34px">${U.esc(T(h.champ).city)} ${U.esc(T(h.champ).name)}</div><div class="dim" style="margin-top:8px">Your season: <b>${h.user.w}-${h.user.l}</b> · ${h.user.res}</div></div><div class="trophy"><div class="cup">🏆</div></div></section>
    <div class="grid g2" style="margin-bottom:16px">
      ${U.slab(`Re-sign your players · ${resign.length}`, resign.length ? resign.map((p) => `<div class="offer"><div class="row">${U.ovrBadge(p)}${U.pname(p, me(), `${p.pos} · age ${p.age} · ${p.arch}`)}<span class="sp"></span>${U.stars(p.stars)}</div>
          <div class="row"><span class="label">Asking</span><b class="mono acc">${U.money(p.ask?.sal || 0)}</b><span class="sp"></span><select data-ryrs="${p.id}" style="height:28px">${[1, 2, 3, 4, 5].map((y) => `<option ${y === (p.ask?.yrs || 2) ? "selected" : ""}>${y}</option>`).join("")}</select><span class="label">yrs</span>
          <button class="btn xs pri" data-act="resign" data-pid="${p.id}">Re-sign</button><button class="btn xs danger" data-act="release" data-pid="${p.id}">Let go</button></div></div>`).join("") + `<div class="dim" style="font-size:12px">You hold Bird rights on these players, so re-signing them is allowed even over the cap. Anyone you don't re-sign leaves when you advance.</div>` : `<div class="empty">No expiring contracts</div>`)}
      ${U.slab("Progression report", rep.length ? `<div class="tbl-wrap"><table class="tbl compact"><thead><tr><th class="l">Player</th><th>Age</th><th>Before</th><th>After</th><th>Δ</th></tr></thead><tbody>${rep.map((r) => { const d = r.after - r.before; return `<tr><td class="l">${U.pname(r.p, me(), null, false)}</td><td>${r.p.age}</td><td>${r.before}</td><td class="hl">${r.after}</td><td class="${d > 0 ? "delta-up" : d < 0 ? "delta-down" : ""}">${d > 0 ? "▲" + d : d < 0 ? "▼" + -d : "—"}</td></tr>`; }).join("")}</tbody></table></div>` : `<div class="empty">—</div>`)}
    </div>
    <div class="grid g2">
      ${awardsSlab(h)}
      ${U.slab(`Retirements · ${retired.length}`, retired.length ? retired.slice(0, 14).map((r) => `<div class="row" style="padding:6px 0;border-bottom:1px solid var(--line)"><b>${U.esc(r.name)}</b><span class="pos">${r.pos}</span><span class="label">age ${r.age}</span><span class="sp"></span><span class="mono">peak ${r.peak}</span></div>`).join("") : `<div class="empty">Nobody retired</div>`)}
    </div>
    <div class="dim" style="margin-top:16px;font-size:12px">Roster after expirations: ${n} players. Free agency is open: <a class="acc" href="#/fa">sign players →</a></div>`;
}
ACT["resign"] = async (el) => {
  const yrs = document.querySelector(`select[data-ryrs="${el.dataset.pid}"]`)?.value;
  await act("resign", { pid: +el.dataset.pid, yrs: +yrs }, { label: "NEGOTIATING" });
  U.toast("Re-signed!");
};
ACT["advance"] = async () => {
  if (S.L.resign.length && !confirm(`${S.L.resign.length} unsigned player(s) will leave in free agency. Continue?`)) return;
  await act("advance", {}, { label: "NEW SEASON" });
  location.hash = "#/draft";
};

export const OPS = { draft, trade, fa, offseason };
