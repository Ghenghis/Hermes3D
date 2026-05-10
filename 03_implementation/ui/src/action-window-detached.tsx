/**
 * Entry module for the detached Action Window. Vite picks this up via the
 * `action-window.html` second entry point in `vite.config.ts`. The pop-out
 * URL is `/action-window.html?detached=1` (Vite serves the file by name) or,
 * when using the dev server's history fallback rewrite, `/action-window?detached=1`.
 *
 * Extra query flag `?with-monitor=1` mounts the Task Monitor drawer alongside
 * the detached panel — used by the W6-4 Playwright spec so it can verify both
 * surfaces inside one page without depending on AppShell wiring (which is
 * still pending W6-3 integration of the components).
 */

import React from "react";
import ReactDOM from "react-dom/client";
import { DetachedActionWindow } from "./components/ActionWindow/DetachedActionWindow";
import { TaskMonitorDrawer } from "./components/TaskMonitor/TaskMonitorDrawer";
import "./styles/globals.css";

const params = new URLSearchParams(window.location.search);
const withMonitor = params.get("with-monitor") === "1";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <DetachedActionWindow />
    {withMonitor && <TaskMonitorDrawer open onClose={() => undefined} />}
  </React.StrictMode>,
);
