// Drives a live-coached game in headless Edge via the DevTools protocol: answers every coaching prompt,
// screenshots each prompt type once, and plays to the final.  node test/uitest.mjs <saveId>
import { spawn } from "node:child_process";
import { mkdtempSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const sid = process.argv[2] || "1";
const OUT = join(dirname(fileURLToPath(import.meta.url)), "shots");
mkdirSync(OUT, { recursive: true });
const port = 9300 + Math.floor(Math.random() * 90);
const edge = spawn(EDGE, ["--headless=new", "--disable-gpu", `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), "nd-"))}`, "--window-size=1500,1000", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let ws, id = 0;
const pending = new Map();
async function connect() {
  for (let i = 0; i < 40; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) {
        ws = new WebSocket(page.webSocketDebuggerUrl);
        await new Promise((r) => (ws.onopen = r));
        ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); } };
        return;
      }
    } catch (e) { /* not up yet */ }
    await sleep(250);
  }
  throw new Error("could not connect to Edge");
}
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => (await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result?.result?.value;
async function shot(name) {
  const r = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(OUT, `${name}.png`), Buffer.from(r.result.data, "base64"));
  console.log("  screenshot", name);
}
const click = (sel) => ev(`(() => { const e = document.querySelector(${JSON.stringify(sel)}); if (!e) return false; e.click(); return true; })()`);

try {
  await connect();
  await send("Page.enable");
  await send("Page.navigate", { url: `http://127.0.0.1:8777/?sid=${sid}#/live` });
  await sleep(2500);
  await click('[data-seg="g-speed"] button[data-v="160"]');
  const seen = new Set();
  let subDone = false;
  const t0 = Date.now();
  while (Date.now() - t0 < 150000) {
    await sleep(400);
    if (!subDone && await ev(`!!document.querySelector('[data-act="cb-out"]')`)) {
      // make a manual substitution through the clipboard
      await click('[data-act="cb-out"]');
      await sleep(100);
      await click('[data-act="cb-in"]');
      subDone = true;
      console.log("queued a substitution");
    }
    const kicker = await ev(`document.querySelector('.coach-card .kicker')?.textContent || ''`);
    if (!kicker) continue;
    const key = kicker.replace(/End of .*/, "End of period");
    if (!seen.has(key)) { seen.add(key); await shot(`ui_${key.replace(/[^a-z]+/gi, "_").toLowerCase()}`); }
    console.log("prompt:", kicker);
    if (kicker === "Final") { await shot("ui_final"); break; }
    if (kicker === "Momentum alert") { (await click('[data-act="dec-timeout"]:not([disabled])')) || (await click('[data-act="dec-read"]')); continue; }
    if (kicker === "Timeout huddle") { await click('[data-act="huddle"][data-c="fire"]'); continue; }
    if (kicker === "Defensive read") { await click('[data-act="read"][data-c="paint"]'); continue; }
    if (kicker === "Halftime film session") { await click('[data-act="film"][data-z="three"]'); continue; }
    if (kicker === "Draw up the final play") { await click('[data-act="fp-call"][data-c="iso"]'); continue; }
    if (kicker === "Execute!") { await sleep(300); await click(".meter-btn"); await sleep(1200); continue; }
    if (kicker === "Huddle result" && await ev(`!!document.querySelector('[data-act="dec-read"]')`) && Math.random() < 0.5) { await click('[data-act="dec-read"]'); continue; }
    await click('[data-act="coach-continue"]');
  }
  const score = await ev(`document.querySelector(".coach-card h2")?.textContent`);
  console.log("STATE:", await ev(`JSON.stringify({idx: __G.idx, n: __G.doc.events.length, el: __G.el, end: __G.endEl, modal: __G.modal, fetching: __G.fetching, paused: __G.paused, q: __G.queue.length, pend: !!__G.pending, fin: !!__G.finalPayload})`));
  await shot("ui_end");
  console.log("RESULT:", score, "| prompts seen:", [...seen].join(", "));
} finally {
  spawn("taskkill", ["/PID", String(edge.pid), "/T", "/F"], { stdio: "ignore" });
  await sleep(500);
  process.exit(0);
}
