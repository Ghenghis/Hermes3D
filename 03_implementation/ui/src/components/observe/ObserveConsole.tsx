import { Activity, Camera, Eye, ShieldCheck, Wifi, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";
import { LockedAction } from "../badges/LockedAction";
import { StatusBadge } from "../badges/StatusBadge";
import { Panel } from "../layout/Panel";
import type { CameraStatus, ObserveStatusResponse } from "../../types/observe";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

const EVENTS = [
  "Layer progress sampled for active print",
  "No spaghetti risk detected in last frame",
  "S1 camera offline; maintenance flag retained",
  "Observe stream is read-only; no printer command path",
];

async function fetchObserveStatus(): Promise<ObserveStatusResponse | null> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/observe/status`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    const payload: unknown = await response.json().catch(() => null);
    if (
      typeof payload !== "object" ||
      payload === null ||
      !Array.isArray((payload as Record<string, unknown>).cameras)
    ) {
      return null;
    }
    return payload as ObserveStatusResponse;
  } catch {
    return null;
  }
}

export function ObserveConsole() {
  const [statusData, setStatusData] = useState<ObserveStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      const data = await fetchObserveStatus();
      if (mounted) {
        setStatusData(data);
        setLoading(false);
      }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 5_000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  const cameras: CameraStatus[] = statusData?.cameras ?? [];
  const onlineCount = cameras.filter((c) => c.health === "reachable").length;
  const totalCount = cameras.length;

  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min">
      <div className="col-span-12 lg:col-span-8">
        <Panel
          id="observe.cameras"
          title="OBSERVE CAMERAS"
          dense
          status={{
            tone: loading ? "cyan" : onlineCount === totalCount && totalCount > 0 ? "green" : "amber",
            label: loading ? "loading" : `${onlineCount}/${totalCount}`,
          }}
          className="h-[360px]"
        >
          <div className="grid h-full grid-cols-1 gap-2 overflow-auto md:grid-cols-2">
            {loading && (
              <div className="col-span-full flex items-center justify-center text-xs text-muted">
                Fetching camera status...
              </div>
            )}
            {!loading && cameras.length === 0 && (
              <div className="col-span-full flex items-center justify-center text-xs text-muted">
                No cameras configured. Backend may be unreachable.
              </div>
            )}
            {cameras.map((camera) => {
              const online = camera.health === "reachable";
              const fps = camera.estimated_fps;
              return (
                <article key={camera.printer_id} className="rounded border border-border bg-surface2/40 p-2 text-xs">
                  <div className="aspect-video rounded border border-border bg-bg flex items-center justify-center relative overflow-hidden">
                    <Camera
                      className={online ? "text-accent-cyan" : "text-muted"}
                      size={28}
                    />
                    {/* Read-only safety badge for S1 (192.168.0.12) */}
                    {camera.read_only && (
                      <span className="absolute top-1 right-1 rounded bg-amber-900/70 px-1.5 py-0.5 text-[9px] font-semibold text-amber-300">
                        READ-ONLY
                      </span>
                    )}
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate font-semibold text-fg">{camera.printer_name}</div>
                      <div className="truncate text-[10px] text-muted font-mono">
                        {camera.camera_url ?? "not configured"}
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <StatusBadge tone={online ? "green" : "muted"} label={online ? "online" : "offline"} />
                      {online ? (
                        <span className="inline-flex items-center gap-0.5 text-[9px] text-accent-cyan">
                          <Wifi size={9} />
                          {camera.response_ms !== null ? `${camera.response_ms}ms` : ""}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-0.5 text-[9px] text-muted">
                          <WifiOff size={9} />
                          offline
                        </span>
                      )}
                    </div>
                  </div>
                  {/* fps indicator — most useful for V400 USB webcam (192.168.0.34) */}
                  <div className="mt-1 flex items-center gap-1 font-mono text-[10px] text-muted">
                    <Activity size={10} />
                    {fps !== null ? `~${fps} fps estimated` : online ? "fps unknown" : "no signal"}
                  </div>
                </article>
              );
            })}
          </div>
        </Panel>
      </div>

      <div className="col-span-12 lg:col-span-4 grid grid-cols-1 gap-2.5">
        <Panel
          id="observe.events"
          title="OBSERVE EVENTS"
          dense
          status={{ tone: "cyan", label: "latest" }}
          className="h-[225px]"
        >
          <ul className="flex h-full flex-col gap-1 overflow-auto text-xs">
            {EVENTS.map((event) => (
              <li key={event} className="flex items-center gap-2 rounded bg-surface2/40 px-2 py-1.5">
                <Eye size={13} className="shrink-0 text-accent-cyan" />
                <span className="truncate text-fg">{event}</span>
              </li>
            ))}
          </ul>
        </Panel>

        <Panel
          id="observe.policy"
          title="OBSERVE POLICY"
          dense
          status={{ tone: "green", label: "safe" }}
          className="h-[125px]"
        >
          <div className="flex items-center gap-2 rounded bg-surface2/40 px-2 py-1.5 text-xs text-fg">
            <ShieldCheck size={14} className="text-accent-green" />
            <span className="min-w-0 flex-1 truncate">Vision stream cannot issue printer commands.</span>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <LockedAction label="Record clip" />
            <LockedAction label="Calibrate camera" />
          </div>
        </Panel>
      </div>
    </div>
  );
}
