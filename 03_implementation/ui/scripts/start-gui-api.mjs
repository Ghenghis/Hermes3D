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
const privateEnv = loadPrivateEnv();
const requestedApiPort = Number(process.env.HERMES3D_GUI_API_PORT ?? process.env.VITE_HERMES3D_BRIDGE_PORT ?? 8765);
const requestedUiPort = Number(process.env.HERMES3D_UI_PORT ?? 5173);
const requestedDesktopPort = Number(process.env.HERMES3D_DESKTOP_COMPAT_PORT ?? 8642);
const apiPort = await choosePort(requestedApiPort, "Hermes3D GUI API");
const desktopPort = process.env.HERMES3D_START_DESKTOP_COMPAT === "0"
  ? null
  : await choosePort(requestedDesktopPort, "Hermes Desktop compatibility API");
const ports = { api: apiPort, ui: requestedUiPort, desktop: desktopPort };
const manifest = writeRuntimeManifest({ implementationRoot, uiRoot, ports });
console.log(`[hermes3d] Runtime ports: API ${manifest.urls.gui_api}${manifest.urls.desktop_compat ? `, Desktop ${manifest.urls.desktop_compat}` : ""}`);
const env = runtimeEnv({
  ...privateEnv,
  ...process.env,
  PYTHONPATH: process.env.PYTHONPATH
    ? `${sourcePath}${path.delimiter}${process.env.PYTHONPATH}`
    : sourcePath,
}, ports);

const children = [
  spawnServer(apiPort, "Hermes3D GUI API"),
];

if (desktopPort) {
  children.push(spawnServer(desktopPort, "Hermes Desktop compatibility API"));
}

const stop = () => {
  for (const child of children) {
    if (!child.killed) {
      child.kill();
    }
  }
};

process.on("SIGINT", stop);
process.on("SIGTERM", stop);
for (const child of children) {
  child.on("exit", (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }
    if (code && code !== 0) {
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
    {
      cwd: implementationRoot,
      env,
      stdio: "inherit",
      windowsHide: true,
    },
  );
}
