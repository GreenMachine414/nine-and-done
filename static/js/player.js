// Player card modal: identity, ratings vs positional ceilings, tendencies, stats history, actions.
import * as U from "./ui.js";
import { S, ACT, act, actLite, query, hooks, T, Pl } from "./state.js";
import { modal, closeModal } from "./app.js";

const GROUPS = [["Scoring", ["ins", "mid", "three", "ft", "post"]], ["Playmaking", ["pass", "hand", "iq"]], ["Defense", ["perd", "intd", "stl", "blk"]], ["Physical", ["reb", "ath", "sta"]]];

export function openPlayer(pid) {
  const L = S.L;
  const p = Pl(pid);
  if (!p) { U.toast("That player has retired.", true); return; }
  const t = p.tid >= 0 ? T(p.tid) : null;
  const ceil = L.consts.ceil[p.pos];
  const lab = L.consts.attr_label;
  const status = p.tid === -1 ? "Free agent" : p.tid === -2 ? `Draft prospect · ${p.dclass} class` : `${t.city} ${t.name}`;
  const isProspect = p.tid === -2;
  const potTxt = U.potText(p);
  const fog = !!p.fog;

  const attrs = GROUPS.map(([g, ks]) => `<div class="attr-group">${g}</div>` + ks.map((k) => {
    const v = p.a[k], c = ceil[k];
    if (v === undefined) {
      return `<div class="attr"><div class="top"><span>${lab[k]}</span><span class="v unk">??<span class="mute" style="font-weight:400"> / ${c}</span></span></div>
        <div class="bar unk"><span class="ceil" style="left:${c}%" title="${p.pos} ceiling: ${c}"></span></div></div>`;
    }
    const col = v >= 85 ? "var(--volt)" : v >= 72 ? "var(--acc)" : v >= 55 ? "#6b7488" : "#454c5c";
    return `<div class="attr"><div class="top"><span>${lab[k]}</span><span class="v" style="color:${col}">${v}<span class="mute" style="font-weight:400"> / ${c}</span></span></div>
      <div class="bar"><i style="width:${v}%;background:${col}"></i><span class="ceil" style="left:${c}%" title="${p.pos} ceiling: ${c}"></span></div></div>`;
  }).join("")).join("");

  const tt = p.t || { three: 25, mid: 25, rim: 25, post: 25, use: 0, pass: 0 };
  const diet = [["three", "3PT", U.SHOT_COLORS.three], ["mid", "Mid", U.SHOT_COLORS.mid], ["rim", "Rim", U.SHOT_COLORS.rim], ["post", "Post", U.SHOT_COLORS.post]];
  const tend = fog ? `<div class="empty" style="padding:14px">Tendencies unknown. Scout him further to learn his game.</div>
    <div class="row wrap" style="gap:8px">${p.scout.step < p.scout.max ? `<button class="btn sm pri" data-act="pm-scout" data-pid="${p.id}" ${S.L.scout.pts >= p.scout.cost ? "" : "disabled"}>🔭 Scout (${p.scout.cost} pts)</button>` : `<span class="chip good">Fully scouted</span>`}<span class="label">You have ${S.L.scout.pts} pts · report ${p.scout.step}/${p.scout.max}</span></div>` : `<div class="diet">${diet.map(([k, , c]) => `<i style="width:${tt[k]}%;background:${c}"></i>`).join("")}</div>
    <div class="legend">${diet.map(([k, l, c]) => `<span><i style="background:${c}"></i>${l} ${tt[k]}%</span>`).join("")}</div>
    <div class="grid g2" style="margin-top:14px;gap:12px">
      <div><div class="row"><span class="label">Usage</span><span class="sp"></span><span class="mono">${tt.use}</span></div><div class="bar" style="margin-top:6px"><i style="width:${tt.use}%"></i></div></div>
      <div><div class="row"><span class="label">Pass first</span><span class="sp"></span><span class="mono">${tt.pass}</span></div><div class="bar" style="margin-top:6px"><i style="width:${tt.pass}%"></i></div></div>
      <div><div class="row"><span class="label">Clutch</span><span class="sp"></span><span class="mono">${p.clutch}</span></div><div class="bar" style="margin-top:6px"><i style="width:${p.clutch}%;background:var(--hot)"></i></div></div>
      <div><div class="row"><span class="label">Durability</span><span class="sp"></span><span class="mono">${p.dur}</span></div><div class="bar" style="margin-top:6px"><i style="width:${p.dur}%;background:var(--ice)"></i></div></div>
    </div>`;

  const seasons = Object.keys(p.stats || {}).sort();
  const statRows = seasons.map((k) => {
    const s = U.perGame(p.stats[k]);
    const tm = T(p.stats[k].tid);
    if (!s) return "";
    return `<tr><td class="l">${k.replace("p", "")}${k.endsWith("p") ? ` <span class="chip hot">PO</span>` : ""}</td><td class="l">${tm ? tm.abbr : ""}</td><td>${s.gp}</td><td>${U.f1(s.min)}</td><td class="hl">${U.f1(s.pts)}</td><td>${U.f1(s.reb)}</td><td>${U.f1(s.ast)}</td><td>${U.f1(s.stl)}</td><td>${U.f1(s.blk)}</td><td>${U.pct(s.fgp, 1)}</td><td>${U.pct(s.tpp, 1)}</td><td>${U.pct(s.ftp, 1)}</td></tr>`;
  }).join("");
  const awards = (p.awards || []).filter((a) => a.a !== "CHAMP");
  const rings = (p.awards || []).filter((a) => a.a === "CHAMP").length;

  const m = p.morale ?? 65;
  const log = (p.mlog || []).slice().reverse().map((x) => `<span class="chip ${x.d > 0 ? "good" : x.d < 0 ? "bad" : ""}">${U.esc(x.t)} ${x.d > 0 ? "+" : ""}${x.d}</span>`).join(" ");
  const persona = p.trait ? `<div class="label" style="margin:18px 0 8px">Personality &amp; mood</div>
    <div class="row">${U.traitChip(p)}<span class="sp"></span>${U.moodChip(p)}<b class="mono" style="margin-left:6px">${Math.round(m)}</b></div>
    <div class="dim" style="font-size:12px;margin-top:6px">${U.esc(L.consts.traits[p.trait] || "")}</div>
    ${log ? `<div class="row wrap" style="gap:4px;margin-top:8px">${log}</div>` : ""}
    ${p.tid === L.user ? `<div class="label" style="margin:12px 0 6px">Talk to him <span class="mute">· once per game day</span></div>
      <div class="row wrap" style="gap:6px"><button class="btn xs" data-act="talk" data-pid="${p.id}" data-a="praise">Praise</button>
      <button class="btn xs" data-act="talk" data-pid="${p.id}" data-a="challenge">Challenge him</button>
      <button class="btn xs" data-act="talk" data-pid="${p.id}" data-a="role">Discuss his role</button></div>` : ""}` : "";

  const actions = [];
  if (p.tid === L.user) {
    const onBlock = L.block.players.includes(p.id);
    actions.push(`<button class="btn sm ${onBlock ? "" : "ghost"}" data-act="toggle-block" data-pid="${p.id}">${onBlock ? "Remove from block" : "Put on trade block"}</button>`);
    actions.push(`<button class="btn sm danger" data-act="release" data-pid="${p.id}">Release</button>`);
    const ut = T(L.user).untouch === p.id;
    const usedThisSeason = T(L.user).untouch_s === L.season && T(L.user).untouch && !ut;
    actions.push(ut ? `<button class="btn sm" data-act="untouch" data-pid="0" data-for="${p.id}">🔒 Remove untouchable tag</button>`
      : `<button class="btn sm ghost" data-act="untouch" data-pid="${p.id}" data-for="${p.id}" ${usedThisSeason ? "disabled title='One untouchable per season'" : ""}>🔒 Make untouchable</button>`);
  } else if (p.tid === -1) {
    actions.push(`<button class="btn sm pri" data-act="nego" data-pid="${p.id}" data-kind="fa">Negotiate (asks ${U.money(p.ask?.sal || 0)})</button>`);
  } else if (p.tid >= 0 && T(p.tid).untouch === p.id) {
    actions.push(`<span class="chip lock">🔒 Untouchable: ${U.esc(T(p.tid).abbr)} won't discuss him this season</span>`);
  } else if (p.tid >= 0 && L.derived.trades_open) {
    actions.push(`<button class="btn sm pri" data-act="trade-for" data-pid="${p.id}">Trade for ${U.esc(p.ln)}</button>`);
  }

  modal(`
    <div class="ph-head" style="--tc2:${t?.c2 || "#222"}">
      ${U.avatar(p, t, true)}
      <div><div class="ph-name"><small>#${p.num} · ${p.pos} · ${U.esc(status)}</small>${U.esc(p.fn)} ${U.esc(p.ln)}</div>
        <div class="ph-meta"><span class="chip">${p.age} yrs</span><span class="chip">${U.ht(p.ht)} · ${p.wt} lb</span><span class="chip">${U.esc(p.school)}</span><span class="chip acc">${U.esc(p.arch)}</span>
        ${p.tags.map((x) => `<span class="chip volt">${x}</span>`).join("")}${p.inj ? `<span class="chip bad">✚ ${U.esc(p.inj.type)} · ${p.inj.games > 0 ? "out " + p.inj.games : "day-to-day"}</span>` : ""}${rings ? `<span class="chip volt">${"🏆".repeat(Math.min(rings, 6))}</span>` : ""}</div></div>
      <div style="text-align:right" class="col"><div class="label">Rating</div><div class="row" style="justify-content:flex-end">${U.ovrBadge(p, true)}</div>
        <div class="label">Potential</div><div>${potTxt}</div></div>
    </div>
    <div class="modal-body">
      <div class="grid g4" style="margin-bottom:18px">
        <div class="stat-tile"><div class="label">Contract</div><div class="v" style="font-size:18px">${p.contract ? `${U.money(p.contract.sal)} <span class="mute" style="font-size:12px">× ${p.contract.yrs}y</span>` : p.ask ? `<span class="dim" style="font-size:14px">asks ${U.money(p.ask.sal)}</span>` : "—"}</div></div>
        <div class="stat-tile"><div class="label">Trade value</div><div class="v" style="font-size:18px">${p.tv ?? "—"}</div></div>
        <div class="stat-tile"><div class="label">Drafted</div><div class="v" style="font-size:14px">${p.draft ? `${p.draft.s} · R${p.draft.rd} #${p.draft.no} (${T(p.draft.tid).abbr})` : "Undrafted"}</div></div>
        <div class="stat-tile"><div class="label">Rating trend</div><div style="margin-top:6px">${U.sparkline(p.hist.map((h) => h.ovr), 150, 30)}</div></div>
      </div>
      <div class="grid" style="grid-template-columns: 1.5fr 1fr; gap:22px">
        <div><div class="label" style="margin-bottom:6px">Attributes <span class="mute">· red tick = ${p.pos} ceiling</span></div><div class="attr-grid">${attrs}</div></div>
        <div><div class="label" style="margin-bottom:10px">Shot diet & tendencies</div>${tend}${persona}
          ${awards.length ? `<div class="label" style="margin:18px 0 8px">Honors</div><div class="row wrap" style="gap:6px">${awards.map((a) => `<span class="award-pill" title="${U.esc(L.consts.award_names[a.a] || a.a)}">${a.s} ${({ ALL1: "All-League 1st", ALL2: "All-League 2nd", FMVP: "Finals MVP", AS: "All-Star", "3PT": "3-Pt Champ", DUNK: "Dunk Champ", ASMVP: "All-Star MVP" })[a.a] || a.a}</span>`).join("")}</div>` : ""}
          <div class="row wrap" style="margin-top:20px;gap:8px">${actions.join("")}</div>
        </div>
      </div>
      <div class="label" style="margin:22px 0 6px">Career stats</div>
      ${statRows ? `<div class="tbl-wrap"><table class="tbl compact"><thead><tr><th class="l">Season</th><th class="l">Tm</th><th>GP</th><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th><th>STL</th><th>BLK</th><th>FG%</th><th>3P%</th><th>FT%</th></tr></thead><tbody>${statRows}</tbody></table></div>` : `<div class="empty">No games played yet</div>`}
    </div>`);
}

ACT["talk"] = async (el) => {
  const pid = +el.dataset.pid;
  el.parentElement.querySelectorAll("button").forEach((b) => (b.disabled = true));
  try {
    const t = (await actLite("talk", { pid, approach: el.dataset.a })).talk;
    const p = Pl(pid);
    p.morale = t.morale;
    p.mlog = [...(p.mlog || []), { t: `talk: ${el.dataset.a}`, d: t.delta }].slice(-6);
    hooks.render();
    U.toast(`${t.txt} (${t.delta > 0 ? "+" : ""}${t.delta} mood)`, t.quality === "bad");
    openPlayer(pid);
  } catch (e) {
    U.toast(e.message, true);
    el.parentElement.querySelectorAll("button").forEach((b) => (b.disabled = false));
  }
};

ACT["trade-for"] = (el) => {
  const p = Pl(el.dataset.pid);
  S.ui.tradeTid = p.tid;
  S.ui.tradeTab = "build";
  S.ui.give = { players: [], picks: [] };
  S.ui.get = { players: [p.id], picks: [] };
  S.ui.tradeEval = null;
  closeModal();
  location.hash = "#/trade";
  query("trade_eval", { tid: S.ui.tradeTid, give: S.ui.give, get: S.ui.get })
    .then((r) => { S.ui.tradeEval = r.eval; hooks.render(); }).catch(() => {});
};

ACT["untouch"] = async (el) => {
  const pid = +el.dataset.pid;
  const L = S.L, t = T(L.user);
  if (pid && !confirm("Name him your untouchable? No team can ask about him, and you only get one per season.")) return;
  try {
    await actLite("untouchable", { pid });
    t.untouch = pid || null;
    if (pid) { t.untouch_s = L.season; L.block.players = L.block.players.filter((x) => x !== pid); }
    hooks.render();
    if (el.closest(".modal")) openPlayer(+el.dataset.for);
    U.toast(pid ? "Untouchable. He's off the table." : "Untouchable tag removed.");
  } catch (e) { U.toast(e.message, true); }
};
ACT["pm-scout"] = async (el) => {
  const pid = +el.dataset.pid;
  el.disabled = true;
  try {
    const rep = (await actLite("scout", { pid })).report;
    const p = Pl(pid);
    const cost = p.scout.cost;
    S.L.scout.pts -= cost;
    S.L.scout.lv[String(pid)] = rep.step;
    Object.assign(p, { scout: { ...rep, cost: cost + 1 }, a: rep.known, tags: rep.tags,
      stars: (rep.ovr[0] + rep.ovr[1]) / 2, pstars: (rep.pot[0] + rep.pot[1]) / 2 });
    hooks.render();
    openPlayer(pid);
  } catch (e) { U.toast(e.message, true); el.disabled = false; }
};
