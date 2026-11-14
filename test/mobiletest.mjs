// Phone emulation (390x844, touch) via DevTools: checks every page for horizontal overflow and screenshots it.
// node test/mobiletest.mjs <saveId> <ownerId> [playerId]
import { spawn } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
const [sid, owner, pid] = process.argv.slice(2);
const OUT = join(dirname(fileURLToPath(import.meta.url)), "shots");
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const port = 9300 + Math.floor(Math.random() * 90);
const edge = spawn(EDGE, ["--headless=new", "--disable-gpu", `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), "nd-"))}`, "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, id = 0; const pending = new Map();
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (e) => (await send("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true })).result?.result?.value;
try {
  for (let i = 0; i < 40 && !ws; i++) { try { const l = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); const p = l.find((t) => t.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r)); } } catch {} await sleep(250); }
  ws.onmessage = (m) => { const d = JSON.parse(m.data); pending.get(d.id)?.(d); };
  await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
  await send("Emulation.setTouchEmulationEnabled", { enabled: true });
  await send("Page.navigate", { url: `http://127.0.0.1:8777/?sid=${sid}&owner=${owner}#/hub` });
  await sleep(3000);
  const routes = ["hub", "roster", "schedule", "standings", "rankings", "stats", "awards", "draft", "trade", "fa", "franchise", "teams", "history", "playoffs"];
  for (const r of routes) {
    await ev(`location.hash = "#/${r}"; true`);
    await sleep(700);
    const m = await ev(`JSON.stringify({w: innerWidth, sw: document.documentElement.scrollWidth, wide: [...document.querySelectorAll('body *')].filter(e => { const b = e.getBoundingClientRect(); return b.right > innerWidth + 2 && !e.closest('.tbl-wrap, .order-strip, .ticker, .rail') && getComputedStyle(e).position !== 'fixed'; }).slice(0, 3).map(e => e.tagName + '.' + (e.className?.baseVal ?? e.className)).join(' | ')})`);
    console.log(r.padEnd(10), m);
    if (["hub", "roster", "trade"].includes(r)) { const s = await send("Page.captureScreenshot", { format: "png" }); writeFileSync(join(OUT, `mob_${r}.png`), Buffer.from(s.result.data, "base64")); }
  }
  if (pid) {
    await ev(`location.hash = "#/roster?p=${pid}"; true`); await sleep(900);
    console.log("player modal", await ev(`JSON.stringify({w: innerWidth, sw: document.documentElement.scrollWidth, modal: Math.round(document.querySelector('.modal')?.getBoundingClientRect().width)})`));
    const s = await send("Page.captureScreenshot", { format: "png" }); writeFileSync(join(OUT, "mob_player.png"), Buffer.from(s.result.data, "base64"));
  }
  await ev(`document.querySelector('[data-act="menu"]').click(); true`); await sleep(400);
  console.log("menu drawer", await ev(`JSON.stringify({open: document.body.classList.contains('menu-open'), items: document.querySelectorAll('.rail .nav-item').length, switchVisible: (() => { const b = document.querySelector('[data-act="exit-league"]').getBoundingClientRect(); return b.bottom <= innerHeight && b.height > 0; })()})`));
  const s = await send("Page.captureScreenshot", { format: "png" }); writeFileSync(join(OUT, "mob_menu.png"), Buffer.from(s.result.data, "base64"));
} finally { spawn("taskkill", ["/PID", String(edge.pid), "/T", "/F"], { stdio: "ignore" }); await sleep(300); process.exit(0); }
