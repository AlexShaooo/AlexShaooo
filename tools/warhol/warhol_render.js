// Render frozen-frame SVGs to transparent PNGs with ONE headless Chrome, driven
// over the DevTools protocol using Node's built-in WebSocket (Node >=21). No npm
// dependencies. Portable: Chrome path from $CHROME_PATH, else common locations.
//
//   node tools/warhol_render.js <frames-dir> [<frames-dir> ...]
//   env: CHROME_PATH (browser binary), SCALE (device pixel ratio; default 2)
const fs = require("fs");
const path = require("path");
const http = require("http");
const os = require("os");
const { spawn, execSync } = require("child_process");

function findChrome() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const cands = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium-browser", "/usr/bin/chromium",
  ];
  for (const c of cands) if (fs.existsSync(c)) return c;
  for (const n of ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"]) {
    try { const p = execSync(`command -v ${n}`).toString().trim(); if (p) return p; } catch { /* next */ }
  }
  throw new Error("No Chrome/Chromium found; set CHROME_PATH");
}

const CHROME = findChrome();
const SCALE = Number(process.env.SCALE || 2);
const PORT = 9333;
const DIRS = process.argv.slice(2).map((d) => path.resolve(d));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const getJSON = (url) => new Promise((res, rej) => {
  http.get(url, (r) => { let d = ""; r.on("data", (c) => (d += c)); r.on("end", () => res(JSON.parse(d))); }).on("error", rej);
});

(async () => {
  const sets = DIRS.map((d) => ({ dir: d, man: JSON.parse(fs.readFileSync(path.join(d, "manifest.json"))) }));
  const { w, h } = sets[0].man;
  const udd = fs.mkdtempSync(path.join(os.tmpdir(), "chr-"));
  const chrome = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run", "--no-default-browser-check",
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${udd}`,
  ], { stdio: "ignore" });

  let ver;
  for (let i = 0; i < 100; i++) { try { ver = await getJSON(`http://127.0.0.1:${PORT}/json/version`); break; } catch { await sleep(200); } }
  if (!ver) throw new Error("Chrome DevTools did not come up");

  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  let id = 0; const pending = new Map(); const handlers = [];
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
    else if (m.method) handlers.slice().forEach((fn) => fn(m));
  };
  const send = (method, params, sessionId) =>
    new Promise((res) => { const mid = ++id; pending.set(mid, res); ws.send(JSON.stringify({ id: mid, method, params: params || {}, sessionId })); });

  const { targetId } = await send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
  await send("Page.enable", {}, sessionId);
  await send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: SCALE, mobile: false }, sessionId);
  await send("Emulation.setDefaultBackgroundColorOverride", { color: { r: 0, g: 0, b: 0, a: 0 } }, sessionId);

  const t0 = Date.now();
  let n = 0, total = sets.reduce((s, x) => s + x.man.frames.length, 0);
  for (const { dir, man } of sets) {
    for (const fr of man.frames) {
      const loaded = new Promise((res) => {
        const fn = (m) => { if (m.method === "Page.loadEventFired" && m.sessionId === sessionId) { const i = handlers.indexOf(fn); if (i >= 0) handlers.splice(i, 1); res(); } };
        handlers.push(fn);
      });
      await send("Page.navigate", { url: "file://" + path.join(dir, fr.svg) }, sessionId);
      await loaded;
      const { data } = await send("Page.captureScreenshot",
        { format: "png", clip: { x: 0, y: 0, width: w, height: h, scale: 1 }, captureBeyondViewport: true }, sessionId);
      fs.writeFileSync(path.join(dir, fr.png), Buffer.from(data, "base64"));
      n++;
    }
    console.log(`  rendered ${path.basename(dir)}`);
  }
  ws.close(); chrome.kill();
  await sleep(300);
  try { fs.rmSync(udd, { recursive: true, force: true }); } catch { /* profile still releasing */ }
  console.log(`rendered ${n}/${total} frames @${SCALE}x in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
})().catch((e) => { console.error(e); process.exit(1); });
