import { Camera, Eye, ShieldCheck } from "lucide-react";
import { LockedAction } from "../badges/LockedAction";
import { StatusBadge } from "../badges/StatusBadge";
import { Panel } from "../layout/Panel";

const CAMERAS = [
  { id: "cam-t1", name: "T1 enclosure", state: "online", fps: 12, printer: "FLSUN T1 #1" },
  { id: "cam-v400", name: "V400 bed", state: "online", fps: 10, printer: "FLSUN V400" },
  { id: "cam-s1", name: "S1 maintenance", state: "offline", fps: 0, printer: "FLSUN S1" },
  { id: "cam-lab", name: "Lab overview", state: "online", fps: 6, printer: "Fleet" },
];

const EVENTS = [
  "Layer progress sampled for active print",
  "No spaghetti risk detected in last frame",
  "S1 camera offline; maintenance flag retained",
  "Observe stream is read-only; no printer command path",
];

export function ObserveConsole() {
  const online = CAMERAS.filter((camera) => camera.state === "online").length;

  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min">
      <div className="col-span-12 lg:col-span-8">
        <Panel
          id="observe.cameras"
          title="OBSERVE CAMERAS"
          dense
          status={{ tone: online === CAMERAS.length ? "green" : "amber", label: `${online}/${CAMERAS.length}` }}
          className="h-[360px]"
        >
          <div className="grid h-full grid-cols-1 gap-2 overflow-auto md:grid-cols-2">
            {CAMERAS.map((camera) => (
              <article key={camera.id} className="rounded border border-border bg-surface2/40 p-2 text-xs">
                <div className="aspect-video rounded border border-border bg-bg flex items-center justify-center">
                  <Camera className={camera.state === "online" ? "text-accent-cyan" : "text-muted"} size={28} />
                </div>
                <div className="mt-2 flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate font-semibold text-fg">{camera.name}</div>
                    <div className="truncate text-[10px] text-muted">{camera.printer}</div>
                  </div>
                  <StatusBadge tone={camera.state === "online" ? "green" : "muted"} label={camera.state} />
                </div>
                <div className="mt-1 font-mono text-[10px] text-muted">{camera.fps} fps observed</div>
              </article>
            ))}
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
