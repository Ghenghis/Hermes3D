import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { choosePort, runtimeEnv, writeRuntimeManifest } from "./runtime-ports.mjs";

const scriptPath = fileURLToPath(import.meta.url);
const uiRoot = path.resolve(path.dirname(scriptPath), "..");
const implementationRoot = path.resolve(uiRoot, "..");
const sourcePath = path.join(implementationRoot, "src");
const python = process.env.PYTHON ?? "python";
const viteBin = path.join(uiRoot, "node_modules", "vite", "bin", "vite.js");
const privateEnv = loadPrivateEnv();
const requestedApiPort = Number(process.env.HERMES3D_GUI_API_PORT ?? process.env.VITE_HERMES3D_BRIDGE_PORT ?? 8765);
const requestedUiPort = Number(process.env.HERMES3D_UI_PORT ?? 5173);
const requestedDesktopPort = Number(process.env.HERMES3D_DESKTOP_COMPAT_PORT ?? 8642);
const apiPort = await choosePort(requestedApiPort, "Hermes3D GUI API");
const uiPort = await choosePort(requestedUiPort, "Hermes3D UI");
const desktopPort = process.env.HERMES3D_START_DESKTOP_COMPAT === "0"
  ? null
  : await choosePort(requestedDesktopPort, "Hermes Desktop compatibility API");
const ports = { api: apiPort, ui: uiPort, desktop: desktopPort };
const manifest = writeRuntimeManifest({ implementationRoot, uiRoot, ports });
console.log(`[hermes3d] Runtime ports: UI ${manifest.urls.frontend}, API ${manifest.urls.gui_api}${manifest.urls.desktop_compat ? `, Desktop ${manifest.urls.desktop_compat}` : ""}`);
const env = runtimeEnv({
  ...privateEnv,
  ...process.env,
  PYTHONPATH: process.env.PYTHONPATH
    ? `${sourcePath}${path.delimiter}${process.env.PYTHONPATH}`
    : sourcePath,
}, ports);

// Start API servers FIRST and gate on /health before launching Vite.
// Without this gate, Vite's port-5173 listener satisfies Playwright's
// webServer.url probe while uvicorn is still binding, so the page-load
// fetch fan-out hits ERR_CONNECTION_REFUSED. Deterministic, no timeouts.
//
// W9-2f (2026-05-10): serialize the two uvicorn spawns so init_db() on the
// shared SQLite file (var/hermes3d.db) doesn't race across processes. The
// db/init._INIT_LOCK is per-process; with parallel spawn both children
// concurrently call executescript() and the second one fails with
// "sqlite3.OperationalError: database is locked" before commit. By waiting
// for the first server's /health (which fires only after init_db() returns)
// the second process always finds an already-initialized DB and the
// IF-NOT-EXISTS / INSERT-OR-IGNORE paths become no-ops.
const children = [spawnServer(apiPort, "Hermes3D GUI API")];
await waitForHealth(`http://127.0.0.1:${apiPort}/health`, "Hermes3D GUI API");
if (desktopPort) {
  children.push(spawnServer(desktopPort, "Hermes Desktop compatibility API"));
  await waitForHealth(`http://127.0.0.1:${desktopPort}/health`, "Hermes Desktop compatibility API");
}
children.push(spawn(
  process.execPath,
  [viteBin, "--host", "127.0.0.1", "--port", String(uiPort), "--strictPort"],
  { cwd: uiRoot, env, stdio: "inherit", windowsHide: true },
));

let stopping = false;
const stop = () => {
  if (stopping) return;
  stopping = true;
  for (const child of children) {
    if (!child.killed) child.kill();
  }
};

process.on("SIGINT", stop);
process.on("SIGTERM", stop);

for (const child of children) {
  child.on("exit", (code) => {
    if (!stopping && code && code !== 0) {
      stop();
      process.exit(code);
    }
  });
}

function loadPrivateEnv() {
  const envPath = process.env.HERMES3D_PRIVATE_ENV ?? "G:/private/.env";
  if (!fs.existsSync(envPath)) {
    return {};
  }
  const loaded = {};
  const content = fs.readFileSync(envPath, "utf8");
  for (const line of content.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }
    const separator = trimmed.indexOf("=");
    if (separator <= 0) {
      continue;
    }
    const key = trimmed.slice(0, separator).trim();
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) {
      continue;
    }
    loaded[key] = parseEnvValue(trimmed.slice(separator + 1));
  }
  return loaded;
}

function parseEnvValue(value) {
  const trimmed = value.trim();
  if ((trimmed.startsWith('"') && trimmed.endsWith('"')) || (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

function spawnServer(port, label) {
  console.log(`[hermes3d] Starting ${label} on http://127.0.0.1:${port}`);
  return spawn(
    python,
    ["-m", "uvicorn", "hermes3d.api.app:app", "--host", "127.0.0.1", "--port", String(port)],
    { cwd: implementationRoot, env, stdio: "inherit", windowsHide: true },
  );
}

async function waitForHealth(url, label, { timeoutMs = 60_000, intervalMs = 250 } = {}) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(url, { method: "GET" });
      if (res.ok) {
        console.log(`[hermes3d] ${label} ready at ${url}`);
        return;
      }
    } catch {
      // listener not bound yet — back off and retry
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error(`[hermes3d] ${label} did not become healthy at ${url} within ${timeoutMs}ms`);
}
