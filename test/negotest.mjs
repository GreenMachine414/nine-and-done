// Opens the free-agent negotiation table in headless Edge, makes a lowball then a fair offer, screenshots each step.
// node test/negotest.mjs <saveId> <ownerId>   (server must be up)
import { spawn } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const [sid, owner] = process.argv.slice(2);
const OUT = join(dirname(fileURLToPath(import.meta.url)), "shots");
const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = 9300 + Math.floor(Math.random() * 90);
const edge = spawn(EDGE, ["--headless=new", "--disable-gpu", `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), "nd-"))}`, "--window-size=1500,1000", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, id = 0;
const pending = new Map();
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (e) => (await send("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true })).result?.result?.value;
const shot = async (n) => { const r = await send("Page.captureScreenshot", { format: "png" }); writeFileSync(join(OUT, `${n}.png`), Buffer.from(r.result.data, "base64")); console.log("screenshot", n); };
try {
  for (let i = 0; i < 40 && !ws; i++) {
    try { const l = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); const p = l.find((t) => t.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r)); } } catch { /* */ }
    await sleep(250);
  }
  ws.onmessage = (m) => { const d = JSON.parse(m.data); pending.get(d.id)?.(d); };
  await send("Page.navigate", { url: `http://127.0.0.1:8777/?sid=${sid}&owner=${owner}#/fa` });
  await sleep(3000);
  console.log("negotiate buttons:", await ev(`document.querySelectorAll('[data-act="nego"]:not([disabled])').length`));
  await ev(`document.querySelector('[data-act="nego"]:not([disabled])').click(); true`);
  await sleep(1200);
  await shot("nego_open");
  const ask = await ev(`+document.getElementById('nego-sal').value`);
  await ev(`document.getElementById('nego-sal').value = ${(ask * 0.8).toFixed(1)}; document.querySelector('[data-act="nego-offer"]').click(); true`);
  await sleep(1200);
  console.log("after lowball:", await ev(`document.querySelector('.modal .coach-result')?.textContent.trim().slice(0, 120)`));
  await shot("nego_counter");
  const counter = await ev(`+document.getElementById('nego-sal')?.value`);
  if (counter) {
    await ev(`document.querySelector('[data-act="nego-offer"]').click(); true`);
    await sleep(1500);
    console.log("after meeting counter:", await ev(`document.querySelector('.modal .coach-result')?.textContent.trim().slice(0, 120)`));
    await shot("nego_final");
  }
} finally {
  spawn("taskkill", ["/PID", String(edge.pid), "/T", "/F"], { stdio: "ignore" });
  await sleep(400);
  process.exit(0);
}
