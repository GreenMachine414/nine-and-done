// Responsiveness test under simulated network lag (headless Edge + DevTools protocol).
// node test/latencytest.mjs <saveId> <ownerId> [latencyMs]
// Checks that optimistic clicks update the DOM immediately and that live games don't stall on the network.
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [sid, owner, lat = "400"] = process.argv.slice(2);
const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const BASE = process.env.ND_BASE || "http://127.0.0.1:8777";
const port = 9300 + Math.floor(Math.random() * 90);
const edge = spawn(EDGE, ["--headless=new", "--disable-gpu", `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), "nd-"))}`, "--window-size=1500,1000", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, id = 0;
const pending = new Map();
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (e) => (await send("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true })).result?.result?.value;
const waitFor = async (expr, ms = 15000) => { const t = Date.now(); while (Date.now() - t < ms) { if (await ev(expr)) return true; await sleep(100); } return false; };
// time from a click to the DOM reflecting it, measured inside the page
const timedClick = (sel, check) => ev(`new Promise((res) => { const t0 = performance.now(); document.querySelector(${JSON.stringify(sel)}).click();
  const poll = () => (${check}) ? res(Math.round(performance.now() - t0)) : (performance.now() - t0 > 5000 ? res(-1) : requestAnimationFrame(poll)); poll(); })`);

try {
  for (let i = 0; i < 40 && !ws; i++) {
    try {
      const l = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const p = l.find((t) => t.type === "page");
      if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r)); }
    } catch { /* not up */ }
    await sleep(250);
  }
  ws.onmessage = (m) => { const d = JSON.parse(m.data); pending.get(d.id)?.(d); };
  await send("Page.enable");
  await send("Network.enable");
  await send("Page.navigate", { url: `${BASE}/` });
  await sleep(1200);
  await ev(`localStorage.setItem("nd_owner", ${JSON.stringify(owner)}); localStorage.setItem("nd_sid", ${JSON.stringify(sid)}); true`);
  await send("Network.emulateNetworkConditions", { offline: false, latency: +lat, downloadThroughput: 1.5e6, uploadThroughput: 5e5 });
  console.log(`network lag: ${lat} ms per request`);
  await send("Page.navigate", { url: `${BASE}/?sid=${sid}#/roster` });
  await waitFor(`!!document.querySelector('[data-seg="strat-pace"]')`, 20000);

  const cur = await ev(`document.querySelector('[data-seg="strat-pace"] button.on').dataset.v`);
  const target = cur === "fast" ? "slow" : "fast";
  console.log("strategy toggle  ->", await timedClick(`[data-seg="strat-pace"] button[data-v="${target}"]`, `document.querySelector('[data-seg="strat-pace"] button.on')?.dataset.v === "${target}"`), "ms");
  const first = await ev(`document.querySelector('#lineup-tbl tbody tr').dataset.pid`);
  console.log("lineup reorder   ->", await timedClick(`#lineup-tbl tbody tr [data-act="lu-move"][data-d="1"]`, `document.querySelector('#lineup-tbl tbody tr').dataset.pid !== "${first}"`), "ms");
  console.log("auto lineup      ->", await timedClick(`[data-act="auto-lineup"]`, `true`), "ms");

  await ev(`location.hash = "#/trade"; true`);
  await waitFor(`!!document.querySelector('[data-act="trade-toggle"][data-side="get"]')`);
  console.log("trade asset pick ->", await timedClick(`[data-act="trade-toggle"][data-side="get"]`, `!!document.querySelector('.asset.on')`), "ms");
  const t0 = Date.now();
  await waitFor(`(() => { const t = document.querySelector('.trade-mid')?.textContent || ''; return t && !t.includes('thinking'); })()`);
  console.log("  (AI verdict arrived in background after", Date.now() - t0, "ms)");
  console.log("franchise upgrade->", await (async () => { await ev(`location.hash = "#/franchise"; true`); await waitFor(`!!document.querySelector('[data-act="buy-upg"]:not([disabled])')`); return timedClick(`[data-act="buy-upg"]:not([disabled])`, `document.querySelector('.fp-badge .big-num')?.textContent !== undefined`); })(), "ms");

  // live game: sample for stalls (animation drained while waiting on the network)
  await ev(`location.hash = "#/live"; true`);
  await waitFor(`!!window.__G && window.__G.live`, 20000);
  let samples = 0, stalls = 0, decisions = 0;
  const tEnd = Date.now() + 25000;
  while (Date.now() < tEnd) {
    const s = await ev(`(() => { const G = window.__G; if (!G) return null; const drained = G.idx >= G.doc.events.length && G.el >= G.endEl;
      return { stall: drained && G.fetching && !G.modal, modal: !!G.modal, el: G.el }; })()`);
    if (s) { samples++; if (s.stall) stalls++; if (s.modal) { decisions++; await ev(`document.querySelector('[data-act="coach-continue"]')?.click() || document.querySelector('[data-act="dec-read"]')?.click() || document.querySelector('[data-act="film"]')?.click(); true`); } }
    await sleep(100);
  }
  const el = await ev(`window.__G?.el`);
  console.log(`live game: ${Math.round(el)} game-seconds played in 25s at 1x, stalled samples ${stalls}/${samples}, prompts handled ${decisions}`);
  await ev(`(async () => { const r = await fetch('/api/s/${sid}/live', {method:'POST', headers:{'Content-Type':'application/json','X-ND-Owner':${JSON.stringify(owner)}}, body: JSON.stringify({cmd:'sim_rest'})}); return r.status; })()`);
} finally {
  spawn("taskkill", ["/PID", String(edge.pid), "/T", "/F"], { stdio: "ignore" });
  await sleep(400);
  process.exit(0);
}
