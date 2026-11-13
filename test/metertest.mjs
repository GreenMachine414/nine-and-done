// Renders the shot meter in headless Edge, releases it, screenshots it.  node test/metertest.mjs  (server must be up)
import { spawn } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = 9300 + Math.floor(Math.random() * 90);
const edge = spawn(EDGE, ["--headless=new", "--disable-gpu", `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), "nd-"))}`, "--window-size=900,500", "http://127.0.0.1:8777/"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, id = 0;
const pending = new Map();
try {
  for (let i = 0; i < 40 && !ws; i++) {
    try {
      const l = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const p = l.find((t) => t.type === "page");
      if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r)); }
    } catch { /* not up yet */ }
    await sleep(250);
  }
  ws.onmessage = (m) => { const d = JSON.parse(m.data); pending.get(d.id)?.(d); };
  const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async (e) => (await send("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true })).result?.result?.value;
  await sleep(1500);
  await ev(`import('/js/ui.js').then(U => { document.body.innerHTML = '<div style="padding:40px;width:700px" id="mt"></div>'; U.shotMeter(document.getElementById('mt'), 2, (a, g) => { window.__res = [a, g]; }); return true; })`);
  await sleep(700);
  await ev(`document.querySelector('.meter-btn').click()`);
  await sleep(900);
  console.log("meter result:", await ev(`JSON.stringify(window.__res)`));
  const r = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(dirname(fileURLToPath(import.meta.url)), "shots", "meter.png"), Buffer.from(r.result.data, "base64"));
} finally {
  spawn("taskkill", ["/PID", String(edge.pid), "/T", "/F"], { stdio: "ignore" });
  await sleep(400);
  process.exit(0);
}
