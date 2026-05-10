import fs from "node:fs";
import net from "node:net";
import path from "node:path";

const DEFAULT_SCAN_WIDTH = 40;

export async function choosePort(preferredPort, label, options = {}) {
  const scanWidth = Number(options.scanWidth ?? process.env.HERMES3D_PORT_SCAN_WIDTH ?? DEFAULT_SCAN_WIDTH);
  const strict = options.strict ?? process.env.HERMES3D_STRICT_PORTS === "1";
  const preferred = Number(preferredPort);
  if (!Number.isInteger(preferred) || preferred < 1 || preferred > 65535) {
    throw new Error(`${label} port is invalid: ${preferredPort}`);
  }
  if (await portAvailable(preferred)) {
    return preferred;
  }
  if (strict) {
    throw new Error(`${label} port ${preferred} is already in use and HERMES3D_STRICT_PORTS=1.`);
  }
  for (let port = preferred + 1; port <= Math.min(65535, preferred + scanWidth); port += 1) {
    if (await portAvailable(port)) {
      console.log(`[hermes3d] ${label} port ${preferred} is busy; using ${port}.`);
      return port;
    }
  }
  throw new Error(`${label} could not find a free port from ${preferred} to ${preferred + scanWidth}.`);
}

export function writeRuntimeManifest({ implementationRoot, uiRoot, ports }) {
  const tsUtc = new Date().toISOString();
  const manifest = {
    ts_utc: tsUtc,
    host: "127.0.0.1",
    ports,
    urls: {
      frontend: `http://127.0.0.1:${ports.ui}`,
      gui_api: `http://127.0.0.1:${ports.api}`,
      desktop_compat: ports.desktop ? `http://127.0.0.1:${ports.desktop}` : null,
    },
  };
  const varDir = path.join(implementationRoot, "var");
  const publicDir = path.join(uiRoot, "public");
  fs.mkdirSync(varDir, { recursive: true });
  fs.mkdirSync(publicDir, { recursive: true });
  fs.writeFileSync(path.join(varDir, "runtime-ports.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  fs.writeFileSync(path.join(publicDir, "hermes3d-runtime.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  return manifest;
}

export function runtimeEnv(env, ports) {
  const next = {
    ...env,
    HERMES3D_GUI_API_PORT: String(ports.api),
    HERMES3D_UI_PORT: String(ports.ui),
    VITE_HERMES3D_BRIDGE_PORT: String(ports.api),
  };
  if (ports.desktop) {
    next.HERMES3D_DESKTOP_COMPAT_PORT = String(ports.desktop);
  }
  return next;
}

export function portAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once("error", () => resolve(false));
    server.once("listening", () => {
      server.close(() => resolve(true));
    });
    server.listen(port, "127.0.0.1");
  });
}
