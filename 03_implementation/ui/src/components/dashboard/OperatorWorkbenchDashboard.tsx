import {
  Archive,
  Camera,
  ChevronDown,
  ExternalLink,
  GripVertical,
  Images,
  LayoutGrid,
  type LucideIcon,
  Maximize2,
  Minimize2,
  Monitor,
  MoveDown,
  MoveUp,
  Play,
  Printer as PrinterIcon,
  RefreshCw,
  Save,
  Scissors,
  ShieldCheck,
  Sparkles,
  Upload,
  WandSparkles,
  Workflow as WorkflowIcon,
  X,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState, type CSSProperties, type DragEvent, type KeyboardEvent, type MouseEvent, type ReactNode, type WheelEvent } from "react";
import { adapters } from "../../api/adapters";
import { gcodeDownloadUrl, pollSliceUntilTerminal, startSlice, type SliceState } from "../../api/slicer";
import { useStore } from "../../app/store";
import type { Agent } from "../../types/agent";
import type { Job } from "../../types/job";
import type { CameraFeed, CameraStatus, CameraViewSettings, ObserveStatusResponse } from "../../types/observe";
import type { Printer } from "../../types/printer";
import type { GcodeUploadResult } from "../../types/printer-lock";
import type { SystemSnapshot } from "../../types/system";
import type { Workflow } from "../../types/workflow";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;
const WORKBENCH_REFRESH_INTERVAL_MS = 10_000;
const WORKBENCH_REQUEST_TIMEOUT_MS = 8_000;
const WORKBENCH_HEALTH_TIMEOUT_MS = 3_000;
const CAMERA_SNAPSHOT_REFRESH_MS = 10_000;

const WORKBENCH_LAYOUT_KEY = "h3d.operatorWorkbench.layout";
const WORKBENCH_SAVED_LAYOUTS_KEY = "h3d.operatorWorkbench.savedLayouts";
const WORKBENCH_ACTION_TAB_KEY = "h3d.operatorWorkbench.actionTab";
const WORKBENCH_LAYOUT_VERSION = 4;

type SlicerWidgetId = "prusaSlicer" | "flsunSlicer" | "orcaSlicer";
type SlicerModuleId = "prusaslicer" | "flsun_slicer" | "orcaslicer";
type WorkbenchWidgetId = "action" | "cameras" | "printerConsole" | "jobs" | "agents" | "modeler" | "slicer" | "slicerApps" | SlicerWidgetId;
type WidgetSize = "compact" | "standard" | "wide" | "tall" | "hero" | "full";
type LayoutPreset = "production" | "modeling" | "monitoring" | "printer" | "software";
type ActionTab = "model" | "slice" | "printer" | "console";
type WorkbenchModeId = "advanced" | "factory" | "creator" | "inspector" | "custom";

export type OperatorWorkbenchDashboardProps = {
  modeId?: WorkbenchModeId;
  title?: string;
  initialPreset?: LayoutPreset;
  defaultActionTab?: ActionTab;
};

const ALL_WIDGETS: WorkbenchWidgetId[] = ["action", "printerConsole", "cameras", "slicerApps", "prusaSlicer", "flsunSlicer", "orcaSlicer", "modeler", "slicer", "jobs", "agents"];
const DEFAULT_WIDGET_ORDER: WorkbenchWidgetId[] = ["action", "cameras", "slicerApps", "modeler", "printerConsole", "jobs", "agents"];
const DEFAULT_WIDGET_SIZES: Record<WorkbenchWidgetId, WidgetSize> = {
  action: "hero",
  printerConsole: "tall",
  cameras: "wide",
  jobs: "wide",
  agents: "standard",
  modeler: "wide",
  slicer: "wide",
  slicerApps: "wide",
  prusaSlicer: "standard",
  flsunSlicer: "standard",
  orcaSlicer: "standard",
};
const WIDGET_SIZE_ORDER: WidgetSize[] = ["compact", "standard", "wide", "tall", "hero", "full"];

const PRESET_ORDERS: Record<LayoutPreset, WorkbenchWidgetId[]> = {
  production: ["action", "printerConsole", "cameras", "jobs", "agents"],
  modeling: ["action", "modeler", "slicerApps", "slicer", "cameras", "printerConsole", "agents"],
  monitoring: ["cameras", "printerConsole", "jobs", "agents"],
  printer: ["printerConsole", "cameras", "slicerApps", "slicer", "jobs", "agents"],
  software: ["cameras", "slicerApps", "modeler", "printerConsole", "agents"],
};

const SLICER_CARD_CONFIGS: Record<SlicerWidgetId, { moduleId: SlicerModuleId; title: string; shortName: string; bestFor: string; primaryPath: string; candidates: string[] }> = {
  prusaSlicer: {
    moduleId: "prusaslicer",
    title: "PrusaSlicer",
    shortName: "Prusa",
    bestFor: "CLI slicing, 3MF export, proven profile workflows",
    primaryPath: "C:/Program Files/Prusa3D/PrusaSlicer/prusa-slicer-console.exe",
    candidates: [
      "C:/Program Files/Prusa3D/PrusaSlicer/prusa-slicer-console.exe",
      "C:/Program Files/Prusa3D/PrusaSlicer/prusa-slicer.exe",
      "PATH: prusa-slicer-console",
    ],
  },
  flsunSlicer: {
    moduleId: "flsun_slicer",
    title: "FLSUN Slicer",
    shortName: "FLSUN",
    bestFor: "FLSUN printer profiles and vendor-tuned exports",
    primaryPath: "C:/FlsunSlicer2.0/FlsunSlicer.exe",
    candidates: [
      "C:/FlsunSlicer2.0/FlsunSlicer.exe",
      "C:/Program Files/FlsunSlicer/FlsunSlicer.exe",
      "PATH: FlsunSlicer",
    ],
  },
  orcaSlicer: {
    moduleId: "orcaslicer",
    title: "OrcaSlicer",
    shortName: "Orca",
    bestFor: "High-quality modern FDM slicing and calibration workflows",
    primaryPath: "C:/Program Files/OrcaSlicer/orca-slicer.exe",
    candidates: [
      "C:/Program Files/OrcaSlicer/orca-slicer.exe",
      "C:/Program Files/OrcaSlicer/OrcaSlicer.exe",
      "PATH: orca-slicer",
    ],
  },
};

const ACTION_TAB_LABELS: Record<ActionTab, string> = {
  model: "Model",
  slice: "Slice",
  printer: "Print",
  console: "Console",
};

type Gen3DTemplate = {
  id: string;
  name: string;
  source: "local_executor" | "provider_backed";
  description: string;
  outputs: string[];
  requires_provider: string | null;
  requires_reference_image?: boolean;
};

type GeneratedModelResult = {
  jobId: string;
  template: string;
  artifactLabel: string;
  artifactPath: string;
  artifactSize: number;
  packageLabel?: string;
  packagePath?: string;
  packageSize?: number;
  truthGate?: string;
};

type Gen3DProvider = {
  provider_id: string;
  label: string;
  readiness: "available" | "installed_not_running" | "not_installed" | "unavailable";
  weights_present: boolean;
  live_reachable: boolean | null;
};

type SlicerDesktopCandidate = {
  source: string;
  path: string;
  exists: boolean;
  is_executable: boolean;
};

type SlicerWindowRecord = {
  available: boolean;
  status: string;
  reason?: string;
  title?: string;
  process_id?: number;
  process_name?: string;
  process_path?: string;
  preview_url?: string;
  stream_url?: string;
};

type SourceToolSupport = {
  tool_id: string;
  label: string;
  supported_type: string;
  family?: string | null;
  source_status: string;
  source_found: boolean;
  source_path?: string | null;
  version_tag?: string | null;
  upstream_url?: string | null;
  support_modes: string[];
  ui_strategy: string;
  notes?: string;
};

type SlicerDesktopApp = {
  id: SlicerModuleId;
  module_id: SlicerModuleId;
  label: string;
  status: string;
  detected: boolean;
  path: string;
  path_source: string;
  user_path?: string | null;
  default_path: string;
  candidates: SlicerDesktopCandidate[];
  launch_supported: boolean;
  window: SlicerWindowRecord;
  window_available: boolean;
  window_preview_url: string;
  window_stream_url?: string;
  source_support?: SourceToolSupport;
  proof_gate_version: string;
  safety: string;
};

type SlicerLaunchResult = {
  accepted: boolean;
  status: string;
  pid?: number;
  reason?: string;
  proof_event_id?: string;
  app?: SlicerDesktopApp;
};

type ModelerApp = {
  id: string;
  label: string;
  kind: "desktop_modeler" | "web_modeler" | string;
  status: string;
  detected: boolean;
  path: string;
  path_source: string;
  default_path: string;
  candidates: SlicerDesktopCandidate[];
  launch_supported: boolean;
  window: SlicerWindowRecord;
  window_available: boolean;
  window_preview_url: string;
  window_stream_url?: string;
  source_support?: SourceToolSupport;
  safety: string;
};

type ModelerLaunchResult = {
  accepted: boolean;
  status: string;
  pid?: number;
  reason?: string;
  proof_event_id?: string;
  app?: ModelerApp;
};

type WindowInputResult = {
  accepted: boolean;
  status: string;
  reason?: string;
};

const SLICER_APP_ORDER: SlicerModuleId[] = ["flsun_slicer", "prusaslicer", "orcaslicer"];
const MODELER_APP_ORDER = ["comfyui", "openscad", "blender", "freecad"];

type WorkbenchState = {
  printers: Printer[];
  jobs: Job[];
  agents: Agent[];
  workflows: Workflow[];
  system: SystemSnapshot | null;
  cameras: CameraFeed[];
  cameraStatus: Record<string, CameraStatus>;
  templates: Gen3DTemplate[];
  providers: Gen3DProvider[];
};

type WorkbenchEndpointFailure = {
  label: string;
  reason: string;
};

type WorkbenchHealth = {
  status: string;
  service?: string;
};

type WorkbenchLayout = {
  order: WorkbenchWidgetId[];
  sizes: Record<WorkbenchWidgetId, WidgetSize>;
};

type SavedWorkbenchLayout = WorkbenchLayout & {
  name: string;
  savedAt: string;
};

const EMPTY_STATE: WorkbenchState = {
  printers: [],
  jobs: [],
  agents: [],
  workflows: [],
  system: null,
  cameras: [],
  cameraStatus: {},
  templates: [],
  providers: [],
};

export function OperatorWorkbenchDashboard({
  modeId = "advanced",
  title = "Production Workbench",
  initialPreset,
  defaultActionTab = "model",
}: OperatorWorkbenchDashboardProps = {}) {
  const setActiveTabId = useStore((state) => state.setActiveTabId);
  const layoutStorageKey = workbenchStorageKey(WORKBENCH_LAYOUT_KEY, modeId);
  const savedLayoutsStorageKey = workbenchStorageKey(WORKBENCH_SAVED_LAYOUTS_KEY, modeId);
  const actionTabStorageKey = workbenchStorageKey(WORKBENCH_ACTION_TAB_KEY, modeId);
  const [state, setState] = useState<WorkbenchState>(EMPTY_STATE);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [lastRefreshUtc, setLastRefreshUtc] = useState<string | null>(null);
  const [refreshFailures, setRefreshFailures] = useState(0);
  const [apiReachable, setApiReachable] = useState<boolean | null>(null);
  const [endpointFailures, setEndpointFailures] = useState<WorkbenchEndpointFailure[]>([]);
  const [widgetOrder, setWidgetOrder] = useState<WorkbenchWidgetId[]>(() => readWorkbenchLayout(layoutStorageKey, initialPreset).order);
  const [widgetSizes, setWidgetSizes] = useState<Record<WorkbenchWidgetId, WidgetSize>>(() => readWorkbenchLayout(layoutStorageKey, initialPreset).sizes);
  const [focusedWidget, setFocusedWidget] = useState<WorkbenchWidgetId | null>(null);
  const [actionTab, setActionTab] = useState<ActionTab>(() => readActionTab(actionTabStorageKey, defaultActionTab));
  const [draggingWidget, setDraggingWidget] = useState<WorkbenchWidgetId | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [savedLayouts, setSavedLayouts] = useState<SavedWorkbenchLayout[]>(() => readSavedLayouts(savedLayoutsStorageKey));
  const [layoutName, setLayoutName] = useState("Shop workbench");
  const refreshInFlightRef = useRef(false);

  const refresh = useCallback(async () => {
    if (refreshInFlightRef.current) {
      return;
    }
    refreshInFlightRef.current = true;
    setRefreshing(true);
    try {
      const results = await Promise.all([
        withWorkbenchTimeout<WorkbenchHealth | null>("api health", fetchWorkbenchHealth(), null, WORKBENCH_HEALTH_TIMEOUT_MS),
        withWorkbenchTimeout<Printer[]>("printers", adapters.getPrinters(), []),
        withWorkbenchTimeout<Job[]>("jobs", adapters.getJobs("printing,queued,running,completed,failed,cancelled"), []),
        withWorkbenchTimeout<Agent[]>("agents", adapters.getAgents(), []),
        withWorkbenchTimeout<Workflow[]>("workflows", adapters.getActiveWorkflows(), []),
        withWorkbenchTimeout<SystemSnapshot | null>("system", adapters.getSystemSnapshot(), null),
        withWorkbenchTimeout<CameraFeed[]>("cameras", fetchCameras(), []),
        withWorkbenchTimeout<ObserveStatusResponse>("camera status", fetchObserveStatus(), { cameras: [], online: 0, total: 0 }),
        withWorkbenchTimeout<Gen3DTemplate[]>("gen3d templates", fetchGen3DTemplates(), []),
        withWorkbenchTimeout<Gen3DProvider[]>("gen3d runtimes", fetchGen3DProviders(), []),
      ]);
      const health = results[0];
      const apiOk = !health.failed && health.value?.status === "ok";
      setApiReachable(apiOk);
      const printersResult = results[1];
      const printers = printersResult.value;
      setState((current) => {
        const nextPrinters = printersResult.failed ? current.printers : printers;
        const nextActivePrinterIds = new Set(nextPrinters.filter(isLiveWorkbenchPrinter).map((printer) => printer.id));
        const nextCameras = results[6].failed
          ? current.cameras.filter((camera) => nextActivePrinterIds.has(camera.printer_id))
          : results[6].value.filter((camera) => nextActivePrinterIds.has(camera.printer_id));
        const nextCameraStatus = results[7].failed
          ? current.cameraStatus
          : Object.fromEntries(
            results[7].value.cameras
              .filter((camera) => nextActivePrinterIds.has(camera.printer_id))
              .map((camera) => [camera.printer_id, camera]),
          );
        return {
          printers: nextPrinters,
          jobs: results[2].failed ? current.jobs : results[2].value,
          agents: results[3].failed ? current.agents : results[3].value,
          workflows: results[4].failed ? current.workflows : results[4].value,
          system: results[5].failed ? current.system : results[5].value,
          cameras: nextCameras,
          cameraStatus: nextCameraStatus,
          templates: results[8].failed ? current.templates : results[8].value,
          providers: results[9].failed ? current.providers : results[9].value,
        };
      });
      const failures = results
        .filter((result) => result.failed)
        .map((result) => ({ label: result.label, reason: result.reason ?? "request failed" }));
      setEndpointFailures(failures);
      setRefreshFailures(failures.length);
      setLastRefreshUtc(new Date().toISOString());
    } finally {
      refreshInFlightRef.current = false;
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      if (!document.hidden) {
        void refresh();
      }
    }, WORKBENCH_REFRESH_INTERVAL_MS);
    const onVisible = () => {
      if (!document.hidden) {
        void refresh();
      }
    };
    const onWindowFocus = () => {
      void refresh();
    };
    const onSettingsChanged = () => {
      void refresh();
    };
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("focus", onWindowFocus);
    window.addEventListener("hermes3d:settings-changed", onSettingsChanged);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("focus", onWindowFocus);
      window.removeEventListener("hermes3d:settings-changed", onSettingsChanged);
    };
  }, [refresh]);

  useEffect(() => {
    writeWorkbenchLayout({ order: widgetOrder, sizes: widgetSizes }, layoutStorageKey);
  }, [layoutStorageKey, widgetOrder, widgetSizes]);

  useEffect(() => {
    writeActionTab(actionTab, actionTabStorageKey);
  }, [actionTab, actionTabStorageKey]);

  const visibleWidgets = focusedWidget ? [focusedWidget] : widgetOrder;
  const availableWidgets = ALL_WIDGETS.filter((widget) => !widgetOrder.includes(widget));
  const activeWorkflow = state.workflows.find((workflow) => workflow.status === "active") ?? state.workflows[0] ?? null;
  const enabledPrinters = state.printers.filter(isLiveWorkbenchPrinter);
  const inactivePrinters = state.printers.length - enabledPrinters.length;
  const panelState: WorkbenchState = { ...state, printers: enabledPrinters };
  const onlineCameras = Object.values(state.cameraStatus).filter((camera) => camera.health === "reachable").length;
  const activeAgents = state.agents.filter((agent) => agent.status === "active").length;
  const queuedJobs = state.jobs.filter((job) => job.status === "queued").length;
  const printingJobs = state.jobs.filter((job) => job.status === "printing").length;
  const systemOk = state.system?.system_status === "OK";
  const localGen3DTemplates = state.templates.filter((template) => !template.requires_provider).length;
  const liveGen3DRuntimes = state.providers.filter((provider) => provider.readiness === "available").length;
  const backendOffline =
    lastRefreshUtc !== null
    && apiReachable === false
    && state.system === null
    && state.printers.length === 0
    && state.jobs.length === 0
    && state.cameras.length === 0
    && refreshFailures >= 1;
  const partialBackendIssue =
    !backendOffline
    && lastRefreshUtc !== null
    && endpointFailures.length > 0;

  const moveWidget = (widget: WorkbenchWidgetId, direction: "up" | "down") => {
    setWidgetOrder((current) => {
      const index = current.indexOf(widget);
      const target = direction === "up" ? index - 1 : index + 1;
      if (index < 0 || target < 0 || target >= current.length) return current;
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  };

  const applyPreset = (preset: LayoutPreset) => {
    setFocusedWidget(null);
    setWidgetOrder(PRESET_ORDERS[preset]);
    setWidgetSizes((current) => ({
      ...DEFAULT_WIDGET_SIZES,
      ...current,
      printerConsole: "tall",
      cameras: "wide",
      action: "hero",
      modeler: preset === "software" ? "wide" : current.modeler ?? DEFAULT_WIDGET_SIZES.modeler,
      slicer: preset === "software" ? "wide" : current.slicer ?? DEFAULT_WIDGET_SIZES.slicer,
    }));
    if (preset === "production") setActionTab("model");
    if (preset === "modeling") setActionTab("model");
    if (preset === "software") setActionTab("model");
    if (preset === "printer") setActionTab("printer");
    if (preset === "monitoring") setActionTab("printer");
  };

  const resetLayout = () => {
    const fallback = fallbackWorkbenchLayout(initialPreset);
    setFocusedWidget(null);
    setWidgetOrder(fallback.order);
    setWidgetSizes(fallback.sizes);
    setActionTab(defaultActionTab ?? "model");
  };

  const addWidget = (widget: WorkbenchWidgetId) => {
    setFocusedWidget(null);
    setWidgetOrder((current) => (current.includes(widget) ? current : [...current, widget]));
  };

  const removeWidget = (widget: WorkbenchWidgetId) => {
    setFocusedWidget((current) => (current === widget ? null : current));
    setWidgetOrder((current) => (current.length <= 1 ? current : current.filter((item) => item !== widget)));
  };

  const cycleWidgetSize = (widget: WorkbenchWidgetId) => {
    setWidgetSizes((current) => {
      const currentSize = current[widget] ?? DEFAULT_WIDGET_SIZES[widget];
      const currentIndex = WIDGET_SIZE_ORDER.indexOf(currentSize);
      const nextSize = WIDGET_SIZE_ORDER[(currentIndex + 1) % WIDGET_SIZE_ORDER.length] ?? "standard";
      return { ...current, [widget]: nextSize };
    });
  };

  const saveCurrentLayout = () => {
    const name = layoutName.trim() || "Shop workbench";
    const saved: SavedWorkbenchLayout = {
      name,
      order: widgetOrder,
      sizes: widgetSizes,
      savedAt: new Date().toISOString(),
    };
    setSavedLayouts((current) => {
      const next = [saved, ...current.filter((item) => item.name !== name)].slice(0, 12);
      writeSavedLayouts(next, savedLayoutsStorageKey);
      return next;
    });
    setMessage(`Saved dashboard layout: ${name}`);
  };

  const applySavedLayout = (name: string) => {
    const saved = savedLayouts.find((item) => item.name === name);
    if (!saved) return;
    setFocusedWidget(null);
    setWidgetOrder(cleanWidgetOrder(saved.order, false));
    setWidgetSizes(cleanWidgetSizes(saved.sizes));
    setLayoutName(saved.name);
  };

  const handleDrop = (targetWidget: WorkbenchWidgetId) => {
    if (!draggingWidget || draggingWidget === targetWidget) {
      setDraggingWidget(null);
      return;
    }
    setWidgetOrder((current) => {
      const fromIndex = current.indexOf(draggingWidget);
      const toIndex = current.indexOf(targetWidget);
      if (fromIndex < 0 || toIndex < 0) return current;
      const next = [...current];
      next.splice(fromIndex, 1);
      next.splice(toIndex, 0, draggingWidget);
      return next;
    });
    setDraggingWidget(null);
  };

  const openActionWindow = () => {
    setFocusedWidget("action");
  };

  return (
    <div className="operator-workbench flex h-full min-h-0 flex-col gap-2" data-testid="dashboard-root" data-dashboard-mode={modeId}>
      <header className="flex flex-wrap items-center justify-between gap-2 rounded border border-border bg-surface px-3 py-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-fg">{title}</span>
            <StatusPill
              tone={apiReachable === false ? "red" : systemOk ? "green" : "amber"}
              label={apiReachable === false ? "api offline" : state.system?.system_status ?? "loading"}
            />
            <StatusPill tone={localGen3DTemplates > 0 ? "green" : "amber"} label={`${localGen3DTemplates}/${state.templates.length} templates`} />
            <StatusPill tone={liveGen3DRuntimes > 0 ? "green" : "amber"} label={`${liveGen3DRuntimes}/${state.providers.length} runtimes`} />
            <StatusPill tone={onlineCameras === state.cameras.length && state.cameras.length > 0 ? "green" : "amber"} label={`${onlineCameras}/${state.cameras.length} cameras`} />
          </div>
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted">
            <span>{enabledPrinters.length} enabled printers</span>
            {inactivePrinters > 0 && <span>{inactivePrinters} disabled or hidden</span>}
            <span>{printingJobs} active prints</span>
            <span>{queuedJobs} queued</span>
            <span>{activeAgents}/{state.agents.length} agents active</span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <PresetButton label="Production" onClick={() => applyPreset("production")} />
          <PresetButton label="Modeling" onClick={() => applyPreset("modeling")} />
          <PresetButton label="Cameras" onClick={() => applyPreset("monitoring")} />
          <PresetButton label="Printer" onClick={() => applyPreset("printer")} />
          <PresetButton label="Software" onClick={() => applyPreset("software")} />
          <button
            type="button"
            data-testid="operator-workbench-cards-btn"
            onClick={() => setPaletteOpen((open) => !open)}
            className="inline-flex items-center gap-1 rounded border border-border bg-bg/40 px-2 py-1 text-xs font-medium text-fg hover:bg-surface2"
            title="Add, remove, and save dashboard cards"
          >
            <LayoutGrid size={13} />
            Cards
          </button>
          <button
            type="button"
            data-testid="operator-workbench-reset-btn"
            onClick={resetLayout}
            className="inline-flex items-center gap-1 rounded border border-border bg-bg/40 px-2 py-1 text-xs font-medium text-muted hover:bg-surface2 hover:text-fg"
            title="Reset the dashboard panel order"
          >
            <LayoutGrid size={13} />
            Reset
          </button>
          <button
            type="button"
            onClick={() => void refresh()}
            className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2 disabled:opacity-60"
            disabled={refreshing}
            title="Refresh live dashboard data. Printer console reload is inside the console card."
          >
            <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} />
            Refresh Data
          </button>
          <button
            type="button"
            data-testid="dashboard-advanced-action-window-btn"
            onClick={openActionWindow}
            title="Focus the production Action Window"
            className="inline-flex items-center gap-1 rounded border border-accent-blue/40 bg-accent-blue/15 px-2 py-1 text-xs font-semibold text-accent-blue hover:bg-accent-blue/25"
          >
            <Maximize2 size={13} />
            Action Window
          </button>
        </div>
      </header>

      {backendOffline && (
        <BackendOfflineBanner
          refreshing={refreshing}
          failures={refreshFailures}
          onRetry={() => void refresh()}
        />
      )}
      {partialBackendIssue && (
        <BackendPartialBanner
          refreshing={refreshing}
          failures={endpointFailures}
          onRetry={() => void refresh()}
        />
      )}

      <WorkflowQuickRail
        active={actionTab}
        onSelect={(tab, widget) => {
          setActionTab(tab);
          if (widget) setFocusedWidget(widget);
        }}
        workflow={activeWorkflow}
      />

      {message && (
        <div className="rounded border border-border bg-bg/50 px-3 py-2 text-xs text-muted" data-testid="operator-workbench-message">
          {message}
        </div>
      )}

      {paletteOpen && (
        <WorkbenchLayoutEditor
          availableWidgets={availableWidgets}
          activeWidgets={widgetOrder}
          savedLayouts={savedLayouts}
          layoutName={layoutName}
          onLayoutNameChange={setLayoutName}
          onAdd={addWidget}
          onRemove={removeWidget}
          onApplySaved={applySavedLayout}
          onSave={saveCurrentLayout}
        />
      )}

      <div className="operator-workbench-grid min-h-0 flex-1">
        {visibleWidgets.map((widget) => (
          <WorkbenchPanel
            key={widget}
            widget={widget}
            focused={focusedWidget === widget}
            onFocus={() => setFocusedWidget(widget)}
            onRestore={() => setFocusedWidget(null)}
            onMoveUp={() => moveWidget(widget, "up")}
            onMoveDown={() => moveWidget(widget, "down")}
            onRemove={() => removeWidget(widget)}
            onCycleSize={() => cycleWidgetSize(widget)}
            size={widgetSizes[widget] ?? DEFAULT_WIDGET_SIZES[widget]}
            removable={widgetOrder.length > 1}
            dragging={draggingWidget === widget}
            onDragStart={() => setDraggingWidget(widget)}
            onDragEnd={() => setDraggingWidget(null)}
            onDragOver={(event) => event.preventDefault()}
            onDrop={() => handleDrop(widget)}
          >
            {widget === "action" && (
              <ProductionActionWindow
                actionTab={actionTab}
                onActionTabChange={setActionTab}
                state={panelState}
                onMessage={setMessage}
                setActiveTabId={setActiveTabId}
              />
            )}
            {widget === "cameras" && (
              <CameraWall
                cameras={state.cameras}
                statusById={state.cameraStatus}
                onOpenObserve={() => setActiveTabId("observe")}
              />
            )}
            {widget === "printerConsole" && <PrinterConsolePanel printers={enabledPrinters} />}
            {widget === "jobs" && <JobsAndPipelinePanel jobs={state.jobs} printers={enabledPrinters} workflow={activeWorkflow} />}
            {widget === "agents" && <AgentsPanel agents={state.agents} onOpenAgents={() => setActiveTabId("agents")} />}
            {widget === "modeler" && <ModelerToolsPanel templates={state.templates} providers={state.providers} setActiveTabId={setActiveTabId} />}
            {widget === "slicerApps" && <SlicerAppsWorkspacePanel onMessage={setMessage} setActiveTabId={setActiveTabId} />}
            {isSlicerWidgetId(widget) && (
              <SlicerAppsWorkspacePanel
                initialSelected={SLICER_CARD_CONFIGS[widget].moduleId}
                onMessage={setMessage}
                setActiveTabId={setActiveTabId}
              />
            )}
            {widget === "slicer" && <SlicerToolsPanel onMessage={setMessage} setActiveTabId={setActiveTabId} />}
          </WorkbenchPanel>
        ))}
      </div>
    </div>
  );
}

function WorkbenchPanel({
  widget,
  focused,
  onFocus,
  onRestore,
  onMoveUp,
  onMoveDown,
  onRemove,
  onCycleSize,
  size,
  removable,
  dragging,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDrop,
  children,
}: {
  widget: WorkbenchWidgetId;
  focused: boolean;
  onFocus: () => void;
  onRestore: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onRemove: () => void;
  onCycleSize: () => void;
  size: WidgetSize;
  removable: boolean;
  dragging: boolean;
  onDragStart: () => void;
  onDragEnd: () => void;
  onDragOver: (event: DragEvent<HTMLElement>) => void;
  onDrop: () => void;
  children: ReactNode;
}) {
  const meta = WIDGET_META[widget];
  return (
    <section
      data-testid={`operator-widget-${widget}`}
      data-widget-id={widget}
      onDragOver={onDragOver}
      onDrop={onDrop}
      className={[
        "operator-workbench-panel flex min-h-0 flex-col rounded border border-border bg-surface",
        dragging ? "opacity-60 ring-1 ring-accent-blue/50" : "opacity-100",
        focused ? "col-span-12 h-full" : sizeClassName(size),
      ].join(" ")}
    >
      <header className="flex h-9 shrink-0 items-center justify-between gap-2 border-b border-border px-3">
        <div className="flex min-w-0 items-center gap-2">
          <span
            draggable
            onDragStart={onDragStart}
            onDragEnd={onDragEnd}
            className="cursor-move rounded p-0.5 text-muted hover:bg-surface2 hover:text-fg"
            title="Drag to move panel"
            aria-label="Drag to move panel"
          >
            <GripVertical size={13} />
          </span>
          <meta.Icon size={14} className={meta.iconClass} />
          <span className="truncate text-[11px] font-semibold uppercase tracking-wide text-fg">{meta.title}</span>
        </div>
        <div className="flex items-center gap-1">
          <button type="button" onClick={onMoveUp} className="rounded p-1 text-muted hover:bg-surface2 hover:text-fg" title="Move panel earlier">
            <MoveUp size={13} />
          </button>
          <button type="button" onClick={onMoveDown} className="rounded p-1 text-muted hover:bg-surface2 hover:text-fg" title="Move panel later">
            <MoveDown size={13} />
          </button>
          <button type="button" data-testid={`operator-widget-size-${widget}`} onClick={onCycleSize} className="rounded px-1.5 py-1 text-[10px] font-semibold uppercase text-muted hover:bg-surface2 hover:text-fg" title="Cycle card size">
            {size}
          </button>
          <button type="button" onClick={focused ? onRestore : onFocus} className="rounded p-1 text-muted hover:bg-surface2 hover:text-fg" title={focused ? "Restore layout" : "Focus panel"}>
            {focused ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>
          <button type="button" data-testid={`operator-widget-remove-${widget}`} onClick={onRemove} disabled={!removable} className="rounded p-1 text-muted hover:bg-surface2 hover:text-accent-red disabled:cursor-not-allowed disabled:opacity-30" title="Remove card">
            <X size={13} />
          </button>
          <ChevronDown size={13} className="text-muted" />
        </div>
      </header>
      <div className="min-h-0 flex-1 overflow-auto p-3">{children}</div>
    </section>
  );
}

const WIDGET_META: Record<WorkbenchWidgetId, { title: string; Icon: LucideIcon; iconClass: string }> = {
  action: {
    title: "Production Action Window",
    Icon: WandSparkles,
    iconClass: "text-accent-blue",
  },
  cameras: {
    title: "Camera Wall",
    Icon: Camera,
    iconClass: "text-accent-cyan",
  },
  printerConsole: {
    title: "Klipper / Mainsail / Fluidd",
    Icon: Monitor,
    iconClass: "text-accent-green",
  },
  jobs: {
    title: "Pipeline + Jobs",
    Icon: WorkflowIcon,
    iconClass: "text-accent-amber",
  },
  agents: {
    title: "Agent Team",
    Icon: Sparkles,
    iconClass: "text-accent-blue",
  },
  modeler: {
    title: "Modeler Tools",
    Icon: Images,
    iconClass: "text-accent-blue",
  },
  slicer: {
    title: "Slicer Tools",
    Icon: Scissors,
    iconClass: "text-accent-amber",
  },
  slicerApps: {
    title: "Slicer Programs",
    Icon: Scissors,
    iconClass: "text-accent-green",
  },
  prusaSlicer: {
    title: "PrusaSlicer",
    Icon: Scissors,
    iconClass: "text-accent-green",
  },
  flsunSlicer: {
    title: "FLSUN Slicer",
    Icon: Scissors,
    iconClass: "text-accent-cyan",
  },
  orcaSlicer: {
    title: "OrcaSlicer",
    Icon: Scissors,
    iconClass: "text-accent-blue",
  },
};

function WorkbenchLayoutEditor({
  availableWidgets,
  activeWidgets,
  savedLayouts,
  layoutName,
  onLayoutNameChange,
  onAdd,
  onRemove,
  onApplySaved,
  onSave,
}: {
  availableWidgets: WorkbenchWidgetId[];
  activeWidgets: WorkbenchWidgetId[];
  savedLayouts: SavedWorkbenchLayout[];
  layoutName: string;
  onLayoutNameChange: (name: string) => void;
  onAdd: (widget: WorkbenchWidgetId) => void;
  onRemove: (widget: WorkbenchWidgetId) => void;
  onApplySaved: (name: string) => void;
  onSave: () => void;
}) {
  return (
    <section data-testid="operator-workbench-layout-editor" className="grid gap-2 rounded border border-border bg-surface p-2 text-xs lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)_minmax(280px,0.7fr)]">
      <div className="min-w-0">
        <div className="mb-1 font-semibold uppercase tracking-wide text-fg">Active cards</div>
        <div className="flex flex-wrap gap-1.5">
          {activeWidgets.map((widget) => {
            const meta = WIDGET_META[widget];
            return (
              <button
                key={widget}
                type="button"
                data-testid={`operator-card-active-${widget}`}
                onClick={() => onRemove(widget)}
                disabled={activeWidgets.length <= 1}
                className="inline-flex items-center gap-1 rounded border border-border bg-bg/40 px-2 py-1 text-fg hover:bg-surface2 disabled:cursor-not-allowed disabled:opacity-50"
                title={`Remove ${meta.title}`}
              >
                <meta.Icon size={12} className={meta.iconClass} />
                {meta.title}
                <X size={11} />
              </button>
            );
          })}
        </div>
      </div>
      <div className="min-w-0">
        <div className="mb-1 font-semibold uppercase tracking-wide text-fg">Add cards</div>
        <div className="flex flex-wrap gap-1.5">
          {availableWidgets.length === 0 ? (
            <span className="rounded border border-border bg-bg/40 px-2 py-1 text-muted">All cards are on the dashboard</span>
          ) : (
            availableWidgets.map((widget) => {
              const meta = WIDGET_META[widget];
              return (
                <button
                  key={widget}
                  type="button"
                  data-testid={`operator-card-add-${widget}`}
                  onClick={() => onAdd(widget)}
                  className="inline-flex items-center gap-1 rounded border border-accent-cyan/40 bg-accent-cyan/10 px-2 py-1 font-semibold text-accent-cyan hover:bg-accent-cyan/20"
                  title={`Add ${meta.title}`}
                >
                  <meta.Icon size={12} className={meta.iconClass} />
                  {meta.title}
                </button>
              );
            })
          )}
        </div>
      </div>
      <div className="grid min-w-0 gap-1.5">
        <div className="font-semibold uppercase tracking-wide text-fg">Saved layouts</div>
        <div className="flex min-w-0 gap-1.5">
          <input
            value={layoutName}
            onChange={(event) => onLayoutNameChange(event.currentTarget.value)}
            className="min-w-0 flex-1 rounded border border-border bg-bg px-2 py-1 text-xs text-fg"
            placeholder="Layout name"
          />
          <button type="button" data-testid="operator-layout-save-btn" onClick={onSave} className="inline-flex items-center gap-1 rounded border border-accent-green/40 bg-accent-green/10 px-2 py-1 font-semibold text-accent-green hover:bg-accent-green/20">
            <Save size={12} />
            Save
          </button>
        </div>
        <select
          value=""
          onChange={(event) => onApplySaved(event.currentTarget.value)}
          className="rounded border border-border bg-bg px-2 py-1 text-xs text-fg"
        >
          <option value="" disabled>
            {savedLayouts.length === 0 ? "No saved layouts" : "Load saved layout"}
          </option>
          {savedLayouts.map((layout) => (
            <option key={`${layout.name}-${layout.savedAt}`} value={layout.name}>
              {layout.name}
            </option>
          ))}
        </select>
      </div>
    </section>
  );
}

function sizeClassName(size: WidgetSize): string {
  if (size === "compact") return "col-span-12 min-h-[260px] xl:col-span-3";
  if (size === "standard") return "col-span-12 min-h-[360px] xl:col-span-4";
  if (size === "wide") return "col-span-12 min-h-[430px] xl:col-span-6";
  if (size === "tall") return "col-span-12 min-h-[680px] xl:col-span-5";
  if (size === "full") return "col-span-12 min-h-[720px]";
  return "col-span-12 min-h-[560px] xl:col-span-7";
}

function WorkflowQuickRail({
  active,
  workflow,
  onSelect,
}: {
  active: ActionTab;
  workflow: Workflow | null;
  onSelect: (tab: ActionTab, focus?: WorkbenchWidgetId) => void;
}) {
  const steps: Array<{ id: ActionTab; label: string; Icon: LucideIcon; focus?: WorkbenchWidgetId }> = [
    { id: "model", label: "Image / Model", Icon: Images, focus: "action" },
    { id: "slice", label: "Slice", Icon: Scissors, focus: "action" },
    { id: "printer", label: "Upload / Print", Icon: PrinterIcon, focus: "action" },
    { id: "console", label: "Observe / Console", Icon: Camera, focus: "cameras" },
  ];
  return (
    <nav className="grid gap-2 rounded border border-border bg-surface p-2 md:grid-cols-4" aria-label="Production workflow">
      {steps.map((step) => {
        const selected = active === step.id;
        return (
          <button
            key={step.id}
            type="button"
            onClick={() => onSelect(step.id, step.focus)}
            aria-pressed={selected}
            className={[
              "flex items-center gap-2 rounded border px-3 py-2 text-left text-xs transition-colors",
              selected ? "border-accent-blue/60 bg-accent-blue/15 text-accent-blue" : "border-border bg-bg/30 text-fg hover:bg-surface2",
            ].join(" ")}
          >
            <step.Icon size={16} />
            <span className="font-semibold">{step.label}</span>
          </button>
        );
      })}
      <div className="md:col-span-4 flex min-w-0 items-center gap-2 border-t border-border pt-2 text-xs text-muted">
        <WorkflowIcon size={13} />
        <span className="truncate">{workflow ? `${workflow.name} - ${workflow.progress}%` : "No active workflow"}</span>
      </div>
    </nav>
  );
}

function ProductionActionWindow({
  actionTab,
  onActionTabChange,
  state,
  onMessage,
  setActiveTabId,
}: {
  actionTab: ActionTab;
  onActionTabChange: (tab: ActionTab) => void;
  state: WorkbenchState;
  onMessage: (message: string | null) => void;
  setActiveTabId: (id: string) => void;
}) {
  const [generatedModels, setGeneratedModels] = useState<GeneratedModelResult[]>([]);
  const [selectedPrinterId, setSelectedPrinterId] = useState<string>("");
  const activePrinter = state.printers.find((printer) => printer.id === selectedPrinterId) ?? preferredPrinter(state.printers);

  useEffect(() => {
    if (!selectedPrinterId && activePrinter) {
      setSelectedPrinterId(activePrinter.id);
    }
  }, [activePrinter, selectedPrinterId]);

  return (
    <div className="grid h-full min-h-[440px] grid-rows-[auto_minmax(0,1fr)] gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1">
          {(Object.keys(ACTION_TAB_LABELS) as ActionTab[]).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => onActionTabChange(tab)}
              aria-pressed={actionTab === tab}
              className={[
                "rounded border px-3 py-1.5 text-xs font-semibold",
                actionTab === tab ? "border-accent-blue/60 bg-accent-blue/15 text-accent-blue" : "border-border text-muted hover:bg-surface2 hover:text-fg",
              ].join(" ")}
            >
              {ACTION_TAB_LABELS[tab]}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <button type="button" onClick={() => setActiveTabId("gen3d")} className="rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2">Open Gen3D</button>
          <button type="button" onClick={() => setActiveTabId("design")} className="rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2">Open Design</button>
          <button type="button" onClick={() => setActiveTabId("printers")} className="rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2">Open Printers</button>
        </div>
      </div>

      <div className="min-h-0 overflow-auto rounded border border-border bg-bg/30 p-3">
        {actionTab === "model" && (
          <ModelActionPane
            templates={state.templates}
            providers={state.providers}
            onMessage={onMessage}
            onGenerated={(model) => setGeneratedModels((current) => [model, ...current].slice(0, 6))}
            generatedModels={generatedModels}
          />
        )}
        {actionTab === "slice" && (
          <SliceActionPane
            generatedModels={generatedModels}
            onMessage={onMessage}
          />
        )}
        {actionTab === "printer" && (
          <PrintActionPane
            printers={state.printers}
            selectedPrinter={activePrinter}
            selectedPrinterId={selectedPrinterId}
            onPrinterChange={setSelectedPrinterId}
            onMessage={onMessage}
          />
        )}
        {actionTab === "console" && (
          <ConsoleActionPane
            printers={state.printers}
            selectedPrinter={activePrinter}
            selectedPrinterId={selectedPrinterId}
            onPrinterChange={setSelectedPrinterId}
          />
        )}
      </div>
    </div>
  );
}

function ModelActionPane({
  templates,
  providers,
  onMessage,
  onGenerated,
  generatedModels,
}: {
  templates: Gen3DTemplate[];
  providers: Gen3DProvider[];
  onMessage: (message: string | null) => void;
  onGenerated: (model: GeneratedModelResult) => void;
  generatedModels: GeneratedModelResult[];
}) {
  const defaultTemplate = templates.find((template) => template.id === "precision_image_relief") ?? templates.find((template) => template.requires_reference_image) ?? templates[0] ?? null;
  const [prompt, setPrompt] = useState("perfect 1:1 precision relief from reference image");
  const [sizeMm, setSizeMm] = useState(180);
  const [selectedTemplateId, setSelectedTemplateId] = useState(defaultTemplate?.id ?? "precision_image_relief");
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [referenceArtifactId, setReferenceArtifactId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!selectedTemplateId && defaultTemplate) {
      setSelectedTemplateId(defaultTemplate.id);
    }
  }, [defaultTemplate, selectedTemplateId]);

  const selectedTemplate = templates.find((template) => template.id === selectedTemplateId) ?? defaultTemplate;
  const providerReady = !selectedTemplate?.requires_provider
    || providers.find((provider) => provider.provider_id === selectedTemplate.requires_provider)?.readiness === "available";

  const attachReference = async () => {
    if (!referenceFile) {
      onMessage("Select an image before attaching it.");
      return;
    }
    setBusy(true);
    const params = new URLSearchParams({
      evidence_type: "reference_image",
      stage: "INTAKE",
      label: referenceFile.name,
      notes: `dashboard action window reference for prompt: ${prompt}`,
    });
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/artifacts?${params.toString()}`, {
        method: "POST",
        headers: { Accept: "application/json" },
        body: await referenceFile.arrayBuffer(),
        cache: "no-store",
      });
      const payload: unknown = await response.json().catch(() => null);
      const artifactId = parseArtifactId(payload);
      if (!response.ok || !artifactId) {
        onMessage(`Reference image blocked: ${summary(payload, response.statusText)}`);
        return;
      }
      setReferenceArtifactId(artifactId);
      onMessage(`Reference image attached: ${referenceFile.name}`);
      await adapters.emitProofEvent("dashboard.reference.attached", { artifact_id: artifactId, filename: referenceFile.name });
    } catch (error) {
      onMessage(`Reference image blocked: ${errorMessage(error)}`);
    } finally {
      setBusy(false);
    }
  };

  const runGeneration = async () => {
    if (selectedTemplate?.requires_reference_image && !referenceArtifactId) {
      onMessage("Attach the reference image before running this model path.");
      return;
    }
    if (!providerReady) {
      onMessage(`Provider blocked: ${selectedTemplate?.requires_provider ?? "provider"} is not available.`);
      return;
    }
    setBusy(true);
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/generation/run`, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          template_id: selectedTemplateId,
          reference_artifact_id: referenceArtifactId,
          constraints: { size_mm: sizeMm },
        }),
        cache: "no-store",
      });
      const payload: unknown = await response.json().catch(() => null);
      const parsed = parseGeneratedModel(payload);
      if (!response.ok || !parsed) {
        onMessage(`Generation blocked: ${summary(payload, response.statusText)}`);
        return;
      }
      onGenerated(parsed);
      onMessage(`Generated ${parsed.packageLabel ?? parsed.artifactLabel}`);
      await adapters.emitProofEvent("dashboard.generation.run", { accepted: true, job_id: parsed.jobId, template_id: selectedTemplateId });
    } catch (error) {
      onMessage(`Generation blocked: ${errorMessage(error)}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid h-full min-h-0 gap-3 xl:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)]">
      <div className="grid content-start gap-3">
        <label className="grid gap-1 text-xs text-muted">
          <span>Reference Image</span>
          <input
            type="file"
            accept=".png,.jpg,.jpeg,.webp"
            onChange={(event) => {
              setReferenceFile(event.currentTarget.files?.[0] ?? null);
              setReferenceArtifactId(null);
            }}
            className="rounded border border-border bg-bg px-2 py-1 text-xs text-fg file:mr-3 file:rounded file:border-0 file:bg-accent-cyan file:px-2 file:py-1 file:text-xs file:font-semibold file:text-bg"
          />
        </label>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={() => void attachReference()} disabled={busy || !referenceFile} className="inline-flex items-center gap-1 rounded bg-accent-cyan px-3 py-1.5 text-xs font-semibold text-bg disabled:opacity-50">
            <Upload size={13} />
            Attach Image
          </button>
          {referenceArtifactId && <StatusPill tone="green" label="image attached" />}
        </div>
        <label className="grid gap-1 text-xs text-muted">
          <span>Model Path</span>
          <select value={selectedTemplateId} onChange={(event) => setSelectedTemplateId(event.currentTarget.value)} className="rounded border border-border bg-bg px-2 py-1.5 text-xs text-fg">
            {templates.length === 0 && <option value="precision_image_relief">Precision Image Relief</option>}
            {templates.map((template) => (
              <option key={template.id} value={template.id}>
                {template.name}{template.requires_provider ? ` (${template.requires_provider})` : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1 text-xs text-muted">
          <span>Prompt</span>
          <textarea value={prompt} onChange={(event) => setPrompt(event.currentTarget.value)} className="min-h-24 rounded border border-border bg-bg px-2 py-1.5 text-xs text-fg" />
        </label>
        <label className="flex items-center gap-2 text-xs text-muted">
          Size mm
          <input type="number" min={5} max={220} value={sizeMm} onChange={(event) => setSizeMm(Number(event.currentTarget.value))} className="w-24 rounded border border-border bg-bg px-2 py-1 text-xs text-fg" />
        </label>
        <button type="button" onClick={() => void runGeneration()} disabled={busy || !providerReady} className="inline-flex w-fit items-center gap-1 rounded bg-accent-blue px-4 py-2 text-xs font-semibold text-bg disabled:opacity-50">
          <WandSparkles size={14} />
          Generate Model + 3MF
        </button>
      </div>
      <ArtifactResultList models={generatedModels} />
    </div>
  );
}

function SliceActionPane({
  generatedModels,
  onMessage,
}: {
  generatedModels: GeneratedModelResult[];
  onMessage: (message: string | null) => void;
}) {
  const firstStl = generatedModels.find((model) => model.artifactPath.toLowerCase().endsWith(".stl"));
  const [stlPath, setStlPath] = useState(firstStl?.artifactPath ?? "");
  const [sliceState, setSliceState] = useState<SliceState | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!stlPath && firstStl) {
      setStlPath(firstStl.artifactPath);
    }
  }, [firstStl, stlPath]);

  const runSlice = async () => {
    const path = stlPath.trim();
    if (!path) {
      onMessage("Select or paste an STL path before slicing.");
      return;
    }
    setBusy(true);
    setSliceState(null);
    try {
      const accepted = await startSlice({ stl_path: path }, { timeoutMs: 30_000 });
      onMessage(`Slice job accepted: ${accepted.job_id}`);
      const terminal = await pollSliceUntilTerminal(accepted.job_id, {
        intervalMs: 2_000,
        maxMs: 25 * 60_000,
        onProgress: setSliceState,
      });
      setSliceState(terminal);
      onMessage(terminal.status === "completed" ? `Slice complete: ${terminal.gcode_path ?? terminal.job_id}` : `Slice ${terminal.status}: ${terminal.error ?? "see logs"}`);
      await adapters.emitProofEvent("dashboard.slice.run", { job_id: terminal.job_id, status: terminal.status, gcode_path: terminal.gcode_path ?? null });
    } catch (error) {
      onMessage(`Slice blocked: ${errorMessage(error)}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid h-full min-h-0 gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(280px,0.8fr)]">
      <div className="grid content-start gap-3">
        <label className="grid gap-1 text-xs text-muted">
          <span>STL path</span>
          <input value={stlPath} onChange={(event) => setStlPath(event.currentTarget.value)} placeholder="G:\\Github\\Hermes3D\\...\\model.stl" className="rounded border border-border bg-bg px-2 py-1.5 font-mono text-xs text-fg" />
        </label>
        <div className="grid gap-2">
          {generatedModels.map((model) => (
            <button
              key={`${model.jobId}-${model.artifactPath}`}
              type="button"
              onClick={() => setStlPath(model.artifactPath)}
              className="rounded border border-border bg-surface2/30 px-2 py-1.5 text-left text-xs text-fg hover:border-accent-cyan/50"
            >
              <span className="font-semibold">{model.artifactLabel}</span>
              <span className="block truncate font-mono text-[10px] text-muted">{model.artifactPath}</span>
            </button>
          ))}
          {generatedModels.length === 0 && <EmptyState title="No generated STL in this session" detail="Generated models will appear here after the model step returns an STL." />}
        </div>
        <button type="button" onClick={() => void runSlice()} disabled={busy || stlPath.trim() === ""} className="inline-flex w-fit items-center gap-1 rounded bg-accent-blue px-4 py-2 text-xs font-semibold text-bg disabled:opacity-50">
          <Scissors size={14} />
          Slice to G-code
        </button>
      </div>
      <SliceStateCard state={sliceState} busy={busy} />
    </div>
  );
}

function PrintActionPane({
  printers,
  selectedPrinter,
  selectedPrinterId,
  onPrinterChange,
  onMessage,
}: {
  printers: Printer[];
  selectedPrinter: Printer | null;
  selectedPrinterId: string;
  onPrinterChange: (id: string) => void;
  onMessage: (message: string | null) => void;
}) {
  const [gcodeFile, setGcodeFile] = useState<File | null>(null);
  const [gcodePath, setGcodePath] = useState("");
  const [jobId, setJobId] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<GcodeUploadResult | null>(null);
  const printable = selectedPrinter != null && !selectedPrinter.maintenance_flag && selectedPrinter.write_enabled !== false;

  const upload = async (start: boolean) => {
    if (!selectedPrinter) {
      onMessage("Select a printer first.");
      return;
    }
    if (!printable) {
      onMessage(`${selectedPrinter.name} is locked or read-only.`);
      return;
    }
    if (!gcodeFile && !gcodePath.trim()) {
      onMessage("Choose a G-code file or paste a backend-readable G-code path.");
      return;
    }
    if (start && !jobId.trim()) {
      onMessage("Upload + Start requires an approved job ID.");
      return;
    }
    setBusy(true);
    const next = gcodeFile
      ? await adapters.uploadGcodeFile(selectedPrinter.id, gcodeFile, start, "hermes3d", "local-operator", start ? jobId : undefined)
      : await adapters.uploadGcode(selectedPrinter.id, gcodePath, start, "hermes3d", "local-operator", start ? jobId : undefined);
    setResult(next);
    setBusy(false);
    onMessage(next.accepted ? `${next.started ? "Started" : "Uploaded"} ${next.item_path ?? next.gcode_path ?? "G-code"}` : `${next.status ?? "blocked"}: ${next.reason ?? "backend rejected request"}`);
    await adapters.emitProofEvent("dashboard.gcode_upload.requested", {
      printer_id: selectedPrinter.id,
      start,
      accepted: next.accepted,
      uploaded: next.uploaded,
      started: next.started,
      item_path: next.item_path ?? null,
    });
  };

  return (
    <div className="grid h-full min-h-0 gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(260px,0.75fr)]">
      <div className="grid content-start gap-3">
        <PrinterSelect printers={printers} value={selectedPrinterId} onChange={onPrinterChange} />
        <label className="grid gap-1 text-xs text-muted">
          <span>G-code file</span>
          <input type="file" accept=".gcode,.g" onChange={(event) => setGcodeFile(event.currentTarget.files?.[0] ?? null)} className="rounded border border-border bg-bg px-2 py-1 text-xs text-fg file:mr-3 file:rounded file:border-0 file:bg-accent-cyan file:px-2 file:py-1 file:text-xs file:font-semibold file:text-bg" />
        </label>
        <label className="grid gap-1 text-xs text-muted">
          <span>G-code path</span>
          <input value={gcodePath} onChange={(event) => setGcodePath(event.currentTarget.value)} placeholder="G:\\Github\\Hermes3D\\...\\part.gcode" className="rounded border border-border bg-bg px-2 py-1.5 font-mono text-xs text-fg" />
        </label>
        <label className="grid gap-1 text-xs text-muted">
          <span>Approved job ID</span>
          <input value={jobId} onChange={(event) => setJobId(event.currentTarget.value)} className="rounded border border-border bg-bg px-2 py-1.5 font-mono text-xs text-fg" />
        </label>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => void upload(false)} disabled={busy || !printable} className="inline-flex items-center gap-1 rounded border border-border px-3 py-1.5 text-xs font-semibold text-fg hover:bg-surface2 disabled:opacity-50">
            <Upload size={13} />
            Upload G-code
          </button>
          <button type="button" onClick={() => void upload(true)} disabled={busy || !printable || jobId.trim() === ""} className="inline-flex items-center gap-1 rounded bg-accent-green px-3 py-1.5 text-xs font-semibold text-bg disabled:opacity-50">
            <Play size={13} />
            Upload + Start
          </button>
        </div>
      </div>
      <PrinterSafetyCard printer={selectedPrinter} result={result} />
    </div>
  );
}

function ConsoleActionPane({
  printers,
  selectedPrinter,
  selectedPrinterId,
  onPrinterChange,
}: {
  printers: Printer[];
  selectedPrinter: Printer | null;
  selectedPrinterId: string;
  onPrinterChange: (id: string) => void;
}) {
  const url = printerWebConsoleUrl(selectedPrinter);
  const moonrakerUrl = printerMoonrakerApiUrl(selectedPrinter);
  const [loadedUrl, setLoadedUrl] = useState<string | null>(null);
  const [loadStarted, setLoadStarted] = useState(false);
  const [frameLoaded, setFrameLoaded] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    setLoadedUrl(null);
    setLoadStarted(false);
    setFrameLoaded(false);
    setReloadKey((current) => current + 1);
  }, [url]);

  const loadConsole = () => {
    if (!url) return;
    setFrameLoaded(false);
    setLoadStarted(true);
    setLoadedUrl(url);
    setReloadKey((current) => current + 1);
  };

  return (
    <div className="grid h-full min-h-[360px] grid-rows-[auto_minmax(0,1fr)] gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <PrinterSelect printers={printers} value={selectedPrinterId} onChange={onPrinterChange} />
        <PrinterConsoleAddressEditor
          printer={selectedPrinter}
          value={url}
          onSaved={(nextUrl) => {
            setLoadedUrl(nextUrl || null);
            setFrameLoaded(false);
            setReloadKey((current) => current + 1);
          }}
        />
        {url && (
          <button type="button" onClick={loadConsole} className="rounded border border-accent-cyan/40 bg-accent-cyan/10 px-2 py-1 text-xs font-semibold text-accent-cyan hover:bg-accent-cyan/20">
            {loadedUrl ? "Reload Mainsail / Fluidd" : "Load Mainsail / Fluidd"}
          </button>
        )}
        {loadedUrl && (
          <button type="button" onClick={() => setLoadedUrl(null)} className="rounded border border-border px-2 py-1 text-xs text-muted hover:bg-surface2 hover:text-fg">
            Unload
          </button>
        )}
        {url && (
          <a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2">
            <ExternalLink size={13} />
            Open Full Console
          </a>
        )}
        {moonrakerUrl && (
          <a href={`${moonrakerUrl}/server/info`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 text-xs text-muted hover:bg-surface2 hover:text-fg">
            Moonraker
          </a>
        )}
      </div>
      {loadedUrl ? (
        <div className="relative min-h-0">
          {!frameLoaded && (
            <div className="absolute inset-0 z-10 grid place-items-center rounded border border-border bg-bg/80 p-4 text-center text-xs text-muted">
              <div>
                <div className="font-semibold text-fg">Loading {selectedPrinter?.name ?? "printer"} console</div>
                <div className="mt-1 font-mono">{loadedUrl}</div>
                {loadStarted && <div className="mt-2">If the printer UI refuses embedding, use Open Full Console.</div>}
              </div>
            </div>
          )}
          <iframe
            key={`${loadedUrl}-${reloadKey}`}
            title={`${selectedPrinter?.name ?? "Printer"} Mainsail or Fluidd console`}
            src={consoleFrameUrl(loadedUrl, reloadKey)}
            loading="lazy"
            referrerPolicy="no-referrer"
            onLoad={() => setFrameLoaded(true)}
            className="h-full min-h-[300px] w-full rounded border border-border bg-bg"
          />
        </div>
      ) : url ? (
        <EmptyState title="Mainsail / Fluidd paused" detail="Reload the embedded console or open the full printer UI." />
      ) : (
        <EmptyState title="No printer console selected" detail="Select a configured printer to load its local web console." />
      )}
    </div>
  );
}

function CameraWall({
  cameras,
  statusById,
  onOpenObserve,
}: {
  cameras: CameraFeed[];
  statusById: Record<string, CameraStatus>;
  onOpenObserve: () => void;
}) {
  const [liveCameraIds, setLiveCameraIds] = useState<Record<string, boolean>>({});
  const [snapshotTick, setSnapshotTick] = useState(() => Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (!document.hidden) {
        setSnapshotTick(Date.now());
      }
    }, CAMERA_SNAPSHOT_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    setLiveCameraIds((current) => {
      const available = new Set(cameras.map((camera) => camera.printer_id));
      const next = Object.fromEntries(Object.entries(current).filter(([cameraId]) => available.has(cameraId)));
      return Object.keys(next).length === Object.keys(current).length ? current : next;
    });
  }, [cameras]);

  if (cameras.length === 0) {
    return <EmptyState title="No camera feeds" detail="The observe camera API returned no configured feeds." />;
  }
  const activeLiveCount = cameras.filter((camera) => liveCameraIds[camera.printer_id]).length;
  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1">
          {cameras.map((camera) => {
            const status = statusById[camera.printer_id];
            return <StatusPill key={camera.printer_id} tone={status?.health === "reachable" ? "green" : "amber"} label={camera.printer_name} />;
          })}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {activeLiveCount > 0 && (
            <button type="button" onClick={() => setLiveCameraIds({})} className="rounded border border-border px-2 py-1 text-xs text-muted hover:bg-surface2 hover:text-fg">Stop Live</button>
          )}
          <button type="button" onClick={() => setSnapshotTick(Date.now())} className="rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2">Refresh Stills</button>
          <button type="button" onClick={onOpenObserve} className="rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2">Open Observe</button>
        </div>
      </div>
      <div className="grid min-h-0 gap-2 overflow-auto lg:grid-cols-2">
        {cameras.map((camera) => {
          const status = statusById[camera.printer_id];
          const health = status?.health ?? camera.health;
          const live = liveCameraIds[camera.printer_id] === true;
          const imagePath = live ? camera.stream_url : camera.snapshot_url;
          const imageStyle = dashboardCameraImageStyle(camera.view_settings);
          return (
            <article
              key={camera.printer_id}
              data-testid={`dashboard-camera-card-${camera.printer_id}`}
              className="grid min-h-[220px] min-w-0 max-w-full grid-rows-[auto_minmax(0,1fr)_auto] overflow-hidden rounded border border-border bg-bg/40"
            >
              <div className="flex items-center justify-between gap-2 border-b border-border px-2 py-1.5 text-xs">
                <div className="min-w-0">
                  <div className="truncate font-semibold text-fg">{camera.printer_name}</div>
                  <div className="truncate font-mono text-[10px] text-muted">{camera.camera_url ?? "camera URL missing"}</div>
                </div>
                <StatusPill tone={health === "reachable" ? "green" : camera.printer_locked ? "amber" : "muted"} label={live ? "live" : health} />
              </div>
              {camera.camera_url && health !== "unreachable" ? (
                <div className="relative min-h-0 overflow-hidden bg-black">
                  <img
                    src={cameraUrl(imagePath, live ? null : snapshotTick)}
                    alt={`${camera.printer_name} camera ${live ? "stream" : "snapshot"}`}
                    loading="lazy"
                    decoding="async"
                    className="h-full w-full"
                    style={imageStyle}
                  />
                  {camera.view_settings.review_overlay === "plate_frame" && <div className="pointer-events-none absolute inset-[8%] border border-accent-amber/70" />}
                </div>
              ) : health === "unreachable" ? (
                <EmptyState title="Camera unreachable" detail={camera.camera_note} />
              ) : (
                <EmptyState title="Camera URL missing" detail={camera.camera_note} />
              )}
              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border px-2 py-1.5 text-[11px] text-muted">
                <span>{camera.camera_kind}</span>
                <span className={camera.plate_clearance?.state === "clear" ? "text-accent-green" : "text-accent-amber"}>
                  plate {camera.plate_clearance?.state ?? "unknown"}
                </span>
                {typeof status?.estimated_fps === "number" && <span className="font-mono">{status.estimated_fps.toFixed(1)} fps</span>}
                {camera.camera_url && health === "reachable" && (
                  <button
                    type="button"
                    onClick={() => setLiveCameraIds((current) => ({ ...current, [camera.printer_id]: !live }))}
                    className="rounded border border-border px-1.5 py-0.5 text-[10px] text-fg hover:bg-surface2"
                  >
                    {live ? "Snapshot" : "Live"}
                  </button>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function PrinterConsolePanel({ printers }: { printers: Printer[] }) {
  const first = preferredPrinter(printers);
  const [selectedPrinterId, setSelectedPrinterId] = useState(first?.id ?? "");
  const [loadedUrl, setLoadedUrl] = useState<string | null>(null);
  const [frameLoaded, setFrameLoaded] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const selectedPrinter = printers.find((printer) => printer.id === selectedPrinterId) ?? first;
  const url = printerWebConsoleUrl(selectedPrinter);
  const moonrakerUrl = printerMoonrakerApiUrl(selectedPrinter);

  useEffect(() => {
    if (!selectedPrinterId && first) setSelectedPrinterId(first.id);
  }, [first, selectedPrinterId]);

  useEffect(() => {
    setLoadedUrl(null);
    setFrameLoaded(false);
    setReloadKey((current) => current + 1);
  }, [url]);

  const reloadConsole = () => {
    if (!url) return;
    setFrameLoaded(false);
    setLoadedUrl(url);
    setReloadKey((current) => current + 1);
  };

  return (
    <div className="grid h-full min-h-[320px] grid-rows-[auto_minmax(0,1fr)] gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <PrinterSelect printers={printers} value={selectedPrinterId} onChange={setSelectedPrinterId} />
        <PrinterConsoleAddressEditor
          printer={selectedPrinter}
          value={url}
          onSaved={(nextUrl) => {
            setLoadedUrl(nextUrl || null);
            setFrameLoaded(false);
            setReloadKey((current) => current + 1);
          }}
        />
        {url && <button type="button" onClick={reloadConsole} className="rounded border border-accent-cyan/40 bg-accent-cyan/10 px-2 py-1 text-xs font-semibold text-accent-cyan hover:bg-accent-cyan/20">{loadedUrl ? "Reload Mainsail / Fluidd" : "Load Mainsail / Fluidd"}</button>}
        {loadedUrl && <button type="button" onClick={() => setLoadedUrl(null)} className="rounded border border-border px-2 py-1 text-xs text-muted hover:bg-surface2 hover:text-fg">Unload</button>}
        {url && <a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2"><ExternalLink size={13} />Open Full Console</a>}
        {moonrakerUrl && <a href={`${moonrakerUrl}/server/info`} target="_blank" rel="noopener noreferrer" className="rounded border border-border px-2 py-1 text-xs text-muted hover:bg-surface2 hover:text-fg">Moonraker</a>}
      </div>
      {loadedUrl ? (
        <div className="relative min-h-0">
          {!frameLoaded && (
            <div className="absolute inset-0 z-10 grid place-items-center rounded border border-border bg-bg/80 p-4 text-center text-xs text-muted">
              <div>
                <div className="font-semibold text-fg">Loading {selectedPrinter?.name ?? "printer"} console</div>
                <div className="mt-1 font-mono">{loadedUrl}</div>
              </div>
            </div>
          )}
          <iframe
            key={`${loadedUrl}-${reloadKey}`}
            title={`${selectedPrinter?.name ?? "Printer"} Mainsail or Fluidd console`}
            src={consoleFrameUrl(loadedUrl, reloadKey)}
            loading="lazy"
            referrerPolicy="no-referrer"
            onLoad={() => setFrameLoaded(true)}
            className="h-full min-h-[280px] w-full rounded border border-border bg-bg"
          />
        </div>
      ) : url ? (
        <EmptyState title="Mainsail / Fluidd paused" detail="Reload the embedded console or open the full printer UI." />
      ) : (
        <EmptyState title="No console" detail="No printer web URL is configured." />
      )}
    </div>
  );
}

function PrinterConsoleAddressEditor({
  printer,
  value,
  onSaved,
}: {
  printer: Printer | null;
  value: string;
  onSaved: (url: string) => void;
}) {
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setDraft(value);
    setMessage(null);
  }, [printer?.id, value]);

  const save = async () => {
    if (!printer) return;
    const nextUrl = draft.trim();
    setSaving(true);
    setMessage(null);
    try {
      await adapters.saveSettings({ printerUrls: { [printer.id]: nextUrl } });
      await adapters.emitProofEvent("dashboard.printer_console_url.saved", {
        printer_id: printer.id,
        configured: nextUrl.length > 0,
      });
      setMessage("saved");
      onSaved(nextUrl);
    } catch {
      setMessage("save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <label className="flex min-w-[18rem] flex-1 items-center gap-1.5 text-xs text-muted">
      <span className="shrink-0">Address</span>
      <input
        value={draft}
        onChange={(event) => setDraft(event.currentTarget.value)}
        placeholder={printer?.ip ? `http://${printer.ip}` : "http://printer-ip"}
        className="min-w-0 flex-1 rounded border border-border bg-bg px-2 py-1 font-mono text-xs text-fg outline-none focus:border-accent-cyan"
      />
      <button
        type="button"
        onClick={() => void save()}
        disabled={!printer || saving}
        className="rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2 disabled:cursor-not-allowed disabled:opacity-50"
        title="Save this printer web console address"
      >
        {saving ? "Saving" : "Save"}
      </button>
      {message && <span className={message === "saved" ? "text-accent-green" : "text-accent-amber"}>{message}</span>}
    </label>
  );
}

function JobsAndPipelinePanel({ jobs, printers, workflow }: { jobs: Job[]; printers: Printer[]; workflow: Workflow | null }) {
  const printerNames = new Map(printers.map((printer) => [printer.id, printer.name]));
  return (
    <div className="grid h-full min-h-0 gap-3 lg:grid-rows-[auto_minmax(0,1fr)]">
      <section className="rounded border border-border bg-bg/40 p-3">
        <div className="flex items-center justify-between gap-2">
          <div className="font-semibold text-fg">{workflow?.name ?? "No active workflow"}</div>
          {workflow && <StatusPill tone={workflow.status === "active" ? "cyan" : "muted"} label={`${workflow.progress}%`} />}
        </div>
        <div className="mt-2 h-1.5 overflow-hidden rounded bg-surface2">
          <div className="h-full rounded bg-accent-cyan" style={{ width: `${workflow?.progress ?? 0}%` }} />
        </div>
      </section>
      <section className="min-h-0 overflow-auto rounded border border-border bg-bg/40 p-3">
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-fg">Jobs</div>
        {jobs.length === 0 ? (
          <EmptyState title="No jobs" detail="The jobs API returned no rows." />
        ) : (
          <ul className="grid gap-2">
            {jobs.slice(0, 12).map((job) => (
              <li key={job.id} className="rounded border border-border bg-surface2/30 p-2 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate font-semibold text-fg">{job.name}</span>
                  <StatusPill tone={job.status === "completed" ? "green" : job.status === "failed" ? "red" : job.status === "printing" ? "cyan" : "muted"} label={job.status} />
                </div>
                <div className="mt-1 truncate text-[11px] text-muted">{job.printer_id ? printerNames.get(job.printer_id) ?? job.printer_id : "unassigned"}</div>
                <div className="mt-2 h-1 overflow-hidden rounded bg-bg">
                  <div className="h-full rounded bg-accent-blue" style={{ width: `${job.progress}%` }} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function AgentsPanel({ agents, onOpenAgents }: { agents: Agent[]; onOpenAgents: () => void }) {
  if (agents.length === 0) {
    return <EmptyState title="No agents" detail="The agents API returned no registered agents." />;
  }
  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-3">
      <button type="button" onClick={onOpenAgents} className="w-fit rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2">Open Agents</button>
      <ul className="grid content-start gap-2 overflow-auto">
        {agents.map((agent) => (
          <li key={agent.id} className="rounded border border-border bg-bg/40 p-2 text-xs">
            <div className="flex items-center justify-between gap-2">
              <span className="truncate font-semibold text-fg">{agent.role}</span>
              <StatusPill tone={agent.status === "active" ? "green" : agent.status === "error" ? "red" : "muted"} label={agent.status} />
            </div>
            <div className="mt-1 truncate text-[11px] text-muted">{agent.model_provider}</div>
            <div className="mt-1 text-[11px] text-muted">{agent.task_count} tasks</div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function NativeWindowPreview({
  src,
  alt,
  onClickInput,
  onWheelInput,
  onKeyInput,
  onError,
}: {
  src: string;
  alt: string;
  onClickInput: (xRatio: number, yRatio: number, button: "left" | "middle" | "right") => void;
  onWheelInput: (xRatio: number, yRatio: number, deltaY: number) => void;
  onKeyInput: (event: KeyboardEvent<HTMLDivElement>) => void;
  onError: () => void;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const pointerRatio = (event: MouseEvent<HTMLDivElement> | WheelEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const image = imgRef.current;
    if (image?.naturalWidth && image.naturalHeight) {
      const scale = Math.min(rect.width / image.naturalWidth, rect.height / image.naturalHeight);
      const width = image.naturalWidth * scale;
      const height = image.naturalHeight * scale;
      const left = rect.left + (rect.width - width) / 2;
      const top = rect.top + (rect.height - height) / 2;
      return {
        x: clamp01((event.clientX - left) / Math.max(1, width)),
        y: clamp01((event.clientY - top) / Math.max(1, height)),
      };
    }
    return {
      x: clamp01((event.clientX - rect.left) / Math.max(1, rect.width)),
      y: clamp01((event.clientY - rect.top) / Math.max(1, rect.height)),
    };
  };
  const sendPointer = (event: MouseEvent<HTMLDivElement>, button: "left" | "middle" | "right") => {
    event.preventDefault();
    ref.current?.focus();
    const point = pointerRatio(event);
    onClickInput(point.x, point.y, button);
  };

  return (
    <div
      ref={ref}
      tabIndex={0}
      role="application"
      aria-label={alt}
      className="relative h-full w-full cursor-default outline-none ring-0 focus:ring-2 focus:ring-accent-cyan/50"
      onClick={(event) => {
        sendPointer(event, "left");
      }}
      onAuxClick={(event) => sendPointer(event, "middle")}
      onContextMenu={(event) => sendPointer(event, "right")}
      onWheel={(event) => {
        event.preventDefault();
        ref.current?.focus();
        const point = pointerRatio(event);
        onWheelInput(point.x, point.y, event.deltaY);
      }}
      onKeyDown={onKeyInput}
    >
      <img ref={imgRef} src={src} alt={alt} className="pointer-events-none h-full w-full object-contain" onError={onError} draggable={false} />
      <div className="pointer-events-none absolute bottom-2 left-2 rounded border border-border bg-bg/80 px-2 py-1 text-[10px] font-semibold uppercase text-muted">
        Live native stream
      </div>
    </div>
  );
}

function ModelerToolsPanel({
  templates,
  providers,
  setActiveTabId,
}: {
  templates: Gen3DTemplate[];
  providers: Gen3DProvider[];
  setActiveTabId: (id: string) => void;
}) {
  const [apps, setApps] = useState<ModelerApp[]>([]);
  const [selectedId, setSelectedId] = useState("comfyui");
  const [busy, setBusy] = useState(false);
  const [previewKey, setPreviewKey] = useState(Date.now());
  const readyProviders = providers.filter((provider) => provider.readiness === "available").length;

  const refreshApps = useCallback(async () => {
    setBusy(true);
    const next = await fetchModelerApps();
    setApps(next);
    const current = next.find((app) => app.id === selectedId);
    if (!current && next.length > 0) {
      setSelectedId(next.find((app) => app.window_available)?.id ?? next.find((app) => app.detected)?.id ?? next[0].id);
    } else if (current && !current.window_available) {
      const running = next.find((app) => app.window_available);
      if (running) {
        setSelectedId(running.id);
      } else if (current.kind === "web_modeler") {
        const installedDesktop = next.find((app) => app.kind !== "web_modeler" && app.detected);
        if (installedDesktop) setSelectedId(installedDesktop.id);
      }
    }
    setPreviewKey(Date.now());
    setBusy(false);
  }, [selectedId]);

  useEffect(() => {
    void refreshApps();
  }, [refreshApps]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") void refreshApps();
    }, 4_000);
    return () => window.clearInterval(interval);
  }, [refreshApps]);

  const selected = apps.find((app) => app.id === selectedId) ?? apps[0] ?? null;
  const isWebModeler = selected?.kind === "web_modeler";
  const webPreviewUrl = selected && isWebModeler && selected.window_available ? selected.window_preview_url : null;
  const desktopPreviewUrl = selected && !isWebModeler && selected.window_available
    ? desktopWindowPreviewUrl(selected.window.stream_url ?? selected.window_stream_url ?? selected.window.preview_url ?? selected.window_preview_url, previewKey, 6)
    : null;

  const openApp = async (app: ModelerApp) => {
    setBusy(true);
    const result = await launchModelerApp(app.id);
    setBusy(false);
    await refreshApps();
    window.setTimeout(() => void refreshApps(), 1_500);
    if (result.accepted) {
      return;
    }
    if (app.kind === "web_modeler" && app.id === "comfyui") {
      setActiveTabId("gen3d");
    }
  };

  const focusApp = async (app: ModelerApp) => {
    const result = await focusModelerApp(app.id);
    if (!result.accepted) {
      await refreshApps();
    }
  };

  const refreshPreviewSoon = useCallback(() => {
    setPreviewKey(Date.now());
    window.setTimeout(() => setPreviewKey(Date.now()), 200);
    window.setTimeout(() => setPreviewKey(Date.now()), 700);
  }, []);

  const sendPointerClick = (app: ModelerApp, xRatio: number, yRatio: number, button: "left" | "middle" | "right") => {
    void sendModelerWindowInput(app.id, "click", { x_ratio: xRatio, y_ratio: yRatio, button }).then(refreshPreviewSoon);
  };

  const sendWheel = (app: ModelerApp, xRatio: number, yRatio: number, deltaY: number) => {
    void sendModelerWindowInput(app.id, "wheel", { x_ratio: xRatio, y_ratio: yRatio, delta_y: deltaY }).then(refreshPreviewSoon);
  };

  const sendKey = (app: ModelerApp, event: KeyboardEvent<HTMLDivElement>) => {
    if (["Shift", "Control", "Alt", "Meta"].includes(event.key)) return;
    event.preventDefault();
    void sendModelerWindowInput(app.id, "key", {
      key: event.key,
      ctrl: event.ctrlKey || event.metaKey,
      alt: event.altKey,
      shift: event.shiftKey,
    }).then(refreshPreviewSoon);
  };

  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-3">
      <div className="flex flex-wrap items-center gap-2">
        {apps.map((app) => (
          <button
            key={app.id}
            type="button"
            onClick={() => setSelectedId(app.id)}
            className={`rounded border px-2 py-1 text-xs font-semibold ${
              selectedId === app.id
                ? "border-accent-blue/50 bg-accent-blue/15 text-accent-blue"
                : "border-border bg-bg/40 text-muted hover:bg-surface2 hover:text-fg"
            }`}
          >
            {app.label}
          </button>
        ))}
        <StatusPill tone={selected?.window_available ? "green" : selected?.detected ? "amber" : "red"} label={selected?.window_available ? "GUI live" : selected?.detected ? "installed" : "missing"} />
        {selected?.source_support && <StatusPill tone={selected.source_support.source_found ? "green" : selected.source_support.supported_type.startsWith("binary_") ? "amber" : "red"} label={selected.source_support.source_found ? "source ready" : selected.source_support.source_status.replace("_", " ")} />}
        <StatusPill tone={readyProviders > 0 ? "green" : "amber"} label={`${readyProviders}/${providers.length} runtimes`} />
        <button type="button" onClick={() => void refreshApps()} disabled={busy} className="ml-auto rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2 disabled:opacity-50">{busy ? "Refreshing" : "Refresh"}</button>
        {selected && (
          <>
            <button type="button" onClick={() => void openApp(selected)} disabled={busy || (!selected.launch_supported && selected.kind !== "web_modeler")} className="rounded border border-accent-green/40 bg-accent-green/10 px-2 py-1 text-xs font-semibold text-accent-green hover:bg-accent-green/20 disabled:opacity-50">
              {selected.kind === "web_modeler" ? "Open Gen3D" : "Open Program"}
            </button>
            <button type="button" onClick={() => void focusApp(selected)} disabled={busy || selected.kind === "web_modeler" || !selected.window_available} className="rounded border border-accent-cyan/40 bg-accent-cyan/10 px-2 py-1 text-xs font-semibold text-accent-cyan hover:bg-accent-cyan/20 disabled:opacity-50">
              Focus Window
            </button>
          </>
        )}
        <button type="button" onClick={() => setActiveTabId("gen3d")} className="rounded border border-accent-blue/40 bg-accent-blue/10 px-2 py-1 text-xs font-semibold text-accent-blue hover:bg-accent-blue/20">Open 3D Generation</button>
        <button type="button" onClick={() => setActiveTabId("design")} className="rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2">Open Design</button>
      </div>
      <div className="grid min-h-0 gap-3 xl:grid-cols-[minmax(0,1fr)_240px]">
        <section className="min-h-[320px] overflow-hidden rounded border border-border bg-black/70">
          {webPreviewUrl && selected ? (
            <iframe src={webPreviewUrl} title={`${selected.label} web UI`} className="h-full w-full border-0 bg-black" />
          ) : desktopPreviewUrl && selected ? (
            <NativeWindowPreview
              src={desktopPreviewUrl}
              alt={`${selected.label} live desktop GUI`}
              onClickInput={(xRatio, yRatio, button) => sendPointerClick(selected, xRatio, yRatio, button)}
              onWheelInput={(xRatio, yRatio, deltaY) => sendWheel(selected, xRatio, yRatio, deltaY)}
              onKeyInput={(event) => sendKey(selected, event)}
              onError={() => {
                setApps((current) => current.map((app) => app.id === selected.id ? { ...app, window_available: false, window: { ...app.window, available: false, status: "capture_failed", reason: "Desktop screenshot could not be loaded." } } : app));
              }}
            />
          ) : (
            <EmptyState
              title={selected ? `${selected.label} GUI not open` : "No modeler surface detected"}
              detail={selected?.detected ? "Open or start the real modeler app, then refresh this card to show its GUI surface." : "Install or configure the modeler before it can be shown here."}
            />
          )}
        </section>
        <aside className="grid content-start gap-2 overflow-auto rounded border border-border bg-bg/40 p-3 text-xs">
          <div className="font-semibold uppercase tracking-wide text-fg">Modeler Surface</div>
          <KV label="selected" value={selected?.label ?? "-"} />
          <KV label="surface" value={selected?.kind ?? "-"} />
          <KV label="source" value={sourceSupportLabel(selected?.source_support)} />
          <KV label="support" value={selected?.source_support?.supported_type ?? "-"} />
          <KV label="window" value={selected?.window.title ?? selected?.window.reason ?? "not running"} />
          <KV label="path" value={selected?.path ?? "-"} />
          <div className="pt-2 font-semibold uppercase tracking-wide text-fg">Templates</div>
          <div className="grid gap-1">
            {templates.slice(0, 5).map((template) => {
              const provider = template.requires_provider ? providers.find((item) => item.provider_id === template.requires_provider) : null;
              const ready = !template.requires_provider || provider?.readiness === "available";
              return (
                <div key={template.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 rounded border border-border bg-surface2/30 px-2 py-1">
                  <span className="truncate text-muted">{template.name}</span>
                  <StatusPill tone={ready ? "green" : "amber"} label={ready ? "ready" : "offline"} />
                </div>
              );
            })}
          </div>
        </aside>
      </div>
    </div>
  );
}

function SlicerToolsPanel({
  onMessage,
  setActiveTabId,
}: {
  onMessage: (message: string | null) => void;
  setActiveTabId: (id: string) => void;
}) {
  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-3">
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={() => setActiveTabId("jobs")} className="rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2">Open Jobs</button>
        <button type="button" onClick={() => setActiveTabId("artifacts")} className="rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2">Open Artifacts</button>
      </div>
      <SliceActionPane generatedModels={[]} onMessage={onMessage} />
    </div>
  );
}

function SlicerAppsWorkspacePanel({
  initialSelected = "flsun_slicer",
  onMessage,
  setActiveTabId,
}: {
  initialSelected?: SlicerModuleId;
  onMessage: (message: string | null) => void;
  setActiveTabId: (id: string) => void;
}) {
  const [apps, setApps] = useState<SlicerDesktopApp[]>([]);
  const [selectedId, setSelectedId] = useState<SlicerModuleId>(initialSelected);
  const [busy, setBusy] = useState(false);
  const [previewKey, setPreviewKey] = useState(Date.now());

  const refreshApps = useCallback(async () => {
    setBusy(true);
    const next = await fetchSlicerDesktopApps();
    setApps(next);
    const current = next.find((app) => app.id === selectedId);
    if (!current && next.length > 0) {
      setSelectedId(next.find((app) => app.window_available)?.id ?? next[0].id);
    } else if (current && !current.window_available) {
      const running = next.find((app) => app.window_available);
      if (running) setSelectedId(running.id);
    }
    setPreviewKey(Date.now());
    setBusy(false);
  }, [selectedId]);

  useEffect(() => {
    void refreshApps();
  }, [refreshApps]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") void refreshApps();
    }, 4_000);
    return () => window.clearInterval(interval);
  }, [refreshApps]);

  const selected = apps.find((app) => app.id === selectedId) ?? apps[0] ?? null;
  const previewUrl = selected?.window_available
    ? desktopWindowPreviewUrl(selected.window.stream_url ?? selected.window_stream_url ?? selected.window.preview_url ?? selected.window_preview_url, previewKey, 8)
    : null;

  const openApp = async (app: SlicerDesktopApp) => {
    setBusy(true);
    const result = await launchSlicerDesktopApp(app.id);
    onMessage(result.accepted ? `Opened ${app.label}${result.pid ? ` (pid ${result.pid})` : ""}.` : `${app.label} open blocked: ${result.reason ?? result.status}`);
    await refreshApps();
    window.setTimeout(() => void refreshApps(), 1_500);
    setBusy(false);
  };

  const focusApp = async (app: SlicerDesktopApp) => {
    const result = await focusSlicerDesktopApp(app.id);
    onMessage(result.accepted ? `${app.label} focused.` : `${app.label} focus blocked: ${result.reason ?? result.status}`);
    await refreshApps();
  };

  const refreshPreviewSoon = useCallback(() => {
    setPreviewKey(Date.now());
    window.setTimeout(() => setPreviewKey(Date.now()), 200);
    window.setTimeout(() => setPreviewKey(Date.now()), 700);
  }, []);

  const sendPointerClick = (app: SlicerDesktopApp, xRatio: number, yRatio: number, button: "left" | "middle" | "right") => {
    void sendSlicerWindowInput(app.id, "click", { x_ratio: xRatio, y_ratio: yRatio, button }).then((result) => {
      if (!result.accepted) onMessage(`${app.label} input blocked: ${result.reason ?? result.status}`);
      refreshPreviewSoon();
    });
  };

  const sendWheel = (app: SlicerDesktopApp, xRatio: number, yRatio: number, deltaY: number) => {
    void sendSlicerWindowInput(app.id, "wheel", { x_ratio: xRatio, y_ratio: yRatio, delta_y: deltaY }).then((result) => {
      if (!result.accepted) onMessage(`${app.label} scroll blocked: ${result.reason ?? result.status}`);
      refreshPreviewSoon();
    });
  };

  const sendKey = (app: SlicerDesktopApp, event: KeyboardEvent<HTMLDivElement>) => {
    if (["Shift", "Control", "Alt", "Meta"].includes(event.key)) return;
    event.preventDefault();
    void sendSlicerWindowInput(app.id, "key", {
      key: event.key,
      ctrl: event.ctrlKey || event.metaKey,
      alt: event.altKey,
      shift: event.shiftKey,
    }).then((result) => {
      if (!result.accepted) onMessage(`${app.label} key blocked: ${result.reason ?? result.status}`);
      refreshPreviewSoon();
    });
  };

  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-3">
      <div className="flex flex-wrap items-center gap-2">
        {apps.map((app) => (
          <button
            key={app.id}
            type="button"
            onClick={() => setSelectedId(app.id)}
            className={`rounded border px-2 py-1 text-xs font-semibold ${
              selectedId === app.id
                ? "border-accent-green/50 bg-accent-green/15 text-accent-green"
                : "border-border bg-bg/40 text-muted hover:bg-surface2 hover:text-fg"
            }`}
          >
            {app.label}
          </button>
        ))}
        <StatusPill tone={selected?.window_available ? "green" : selected?.detected ? "amber" : "red"} label={selected?.window_available ? "GUI live" : selected?.detected ? "app found" : "missing"} />
        {selected?.source_support && <StatusPill tone={selected.source_support.source_found ? "green" : selected.source_support.supported_type.startsWith("binary_") ? "amber" : "red"} label={selected.source_support.source_found ? "source ready" : selected.source_support.source_status.replace("_", " ")} />}
        {selected?.window.process_id && <StatusPill tone="cyan" label={`pid ${selected.window.process_id}`} />}
        <button type="button" onClick={() => void refreshApps()} disabled={busy} className="ml-auto rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2 disabled:opacity-50">
          {busy ? "Refreshing" : "Refresh"}
        </button>
        {selected && (
          <>
            <button type="button" onClick={() => void openApp(selected)} disabled={!selected.launch_supported || busy} className="rounded border border-accent-green/40 bg-accent-green/10 px-2 py-1 text-xs font-semibold text-accent-green hover:bg-accent-green/20 disabled:opacity-50">
              Open Program
            </button>
            <button type="button" onClick={() => void focusApp(selected)} disabled={!selected.window_available || busy} className="rounded border border-accent-cyan/40 bg-accent-cyan/10 px-2 py-1 text-xs font-semibold text-accent-cyan hover:bg-accent-cyan/20 disabled:opacity-50">
              Focus Window
            </button>
          </>
        )}
        <button type="button" onClick={() => setActiveTabId("design")} className="rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2">
          Slice Tab
        </button>
      </div>

      <div className="grid min-h-0 gap-3 xl:grid-cols-[minmax(0,1fr)_240px]">
        <section className="min-h-[320px] overflow-hidden rounded border border-border bg-black/70">
          {previewUrl && selected ? (
            <NativeWindowPreview
              src={previewUrl}
              alt={`${selected.label} live desktop GUI`}
              onClickInput={(xRatio, yRatio, button) => sendPointerClick(selected, xRatio, yRatio, button)}
              onWheelInput={(xRatio, yRatio, deltaY) => sendWheel(selected, xRatio, yRatio, deltaY)}
              onKeyInput={(event) => sendKey(selected, event)}
              onError={() => {
                setApps((current) => current.map((app) => app.id === selected.id ? { ...app, window_available: false, window: { ...app.window, available: false, status: "capture_failed", reason: "Desktop screenshot could not be loaded." } } : app));
              }}
            />
          ) : (
            <EmptyState
              title={selected ? `${selected.label} GUI not open` : "No slicer app detected"}
              detail={selected?.detected ? "Open the installed slicer program, then refresh this card to show the real desktop GUI." : "Set or install a slicer executable before it can be shown here."}
            />
          )}
        </section>

        <aside className="grid content-start gap-2 overflow-auto rounded border border-border bg-bg/40 p-3 text-xs">
          <div className="font-semibold uppercase tracking-wide text-fg">Program Surface</div>
          <KV label="selected" value={selected?.label ?? "-"} />
          <KV label="source" value={sourceSupportLabel(selected?.source_support)} />
          <KV label="support" value={selected?.source_support?.supported_type ?? "-"} />
          <KV label="window" value={selected?.window.title ?? selected?.window.reason ?? "not running"} />
          <KV label="program" value={selected?.path ?? "-"} />
          <KV label="source" value={selected?.path_source ?? "-"} />
          <div className="pt-2 text-[11px] leading-relaxed text-muted">
            This is a live screenshot of the installed Windows slicer GUI. It does not send printer commands or claim slice success.
          </div>
        </aside>
      </div>
    </div>
  );
}

function ArtifactResultList({ models }: { models: GeneratedModelResult[] }) {
  return (
    <section className="min-h-0 overflow-auto rounded border border-border bg-bg/40 p-3">
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-fg">
        <Archive size={13} />
        Generated Models
      </div>
      {models.length === 0 ? (
        <EmptyState title="No model this session" detail="Run generation and returned 3MF/STL artifacts will appear here." />
      ) : (
        <ul className="grid gap-2">
          {models.map((model) => (
            <li key={`${model.jobId}-${model.artifactPath}`} className="rounded border border-border bg-surface2/30 p-2 text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-semibold text-fg">{model.packageLabel ?? model.artifactLabel}</span>
                <StatusPill tone={model.truthGate === "pass" ? "green" : "cyan"} label={model.truthGate ?? "proof"} />
              </div>
              <div className="mt-1 truncate font-mono text-[10px] text-muted">{model.packagePath ?? model.artifactPath}</div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function SliceStateCard({ state, busy }: { state: SliceState | null; busy: boolean }) {
  return (
    <section className="min-h-0 overflow-auto rounded border border-border bg-bg/40 p-3 text-xs">
      <div className="mb-2 flex items-center gap-2 font-semibold uppercase tracking-wide text-fg">
        <Scissors size={13} />
        Slice Result
        {busy && <span className="ml-auto h-3 w-3 animate-spin rounded-full border-2 border-accent-blue border-t-transparent" />}
      </div>
      {!state ? (
        <EmptyState title="No slice job" detail="Start slicing to produce G-code." />
      ) : (
        <div className="grid gap-2">
          <KV label="status" value={state.status} />
          <KV label="job" value={state.job_id} />
          {state.gcode_path && <KV label="gcode" value={state.gcode_path} />}
          {state.sha256 && <KV label="sha256" value={state.sha256} />}
          {typeof state.layer_count === "number" && <KV label="layers" value={String(state.layer_count)} />}
          {gcodeDownloadUrl(state) && <a href={gcodeDownloadUrl(state) ?? "#"} className="w-fit rounded border border-accent-green/40 bg-accent-green/10 px-2 py-1 text-accent-green" download>Download G-code</a>}
        </div>
      )}
    </section>
  );
}

function PrinterSafetyCard({ printer, result }: { printer: Printer | null; result: GcodeUploadResult | null }) {
  return (
    <section className="min-h-0 overflow-auto rounded border border-border bg-bg/40 p-3 text-xs">
      <div className="mb-2 flex items-center gap-2 font-semibold uppercase tracking-wide text-fg">
        <ShieldCheck size={13} />
        Print Gates
      </div>
      {!printer ? (
        <EmptyState title="No printer selected" detail="Select a configured printer." />
      ) : (
        <div className="grid gap-2">
          <KV label="printer" value={printer.name} />
          <KV label="state" value={printer.status} />
          <KV label="policy" value={printer.safety_policy ?? (printer.write_enabled === false ? "read_only" : "write_enabled")} />
          <KV label="current job" value={printer.current_job ?? "-"} />
          {result && (
            <div className={`rounded border px-2 py-1 ${result.accepted ? "border-accent-green/40 bg-accent-green/10 text-accent-green" : "border-accent-red/40 bg-accent-red/10 text-accent-red"}`}>
              {result.accepted ? `${result.started ? "Started" : "Uploaded"} ${result.item_path ?? result.gcode_path ?? ""}` : `${result.status ?? "blocked"}: ${result.reason ?? "backend rejected request"}`}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function PrinterSelect({ printers, value, onChange }: { printers: Printer[]; value: string; onChange: (id: string) => void }) {
  return (
    <label className="flex min-w-[220px] items-center gap-2 text-xs text-muted">
      Printer
      <select value={value} onChange={(event) => onChange(event.currentTarget.value)} className="min-w-0 flex-1 rounded border border-border bg-bg px-2 py-1.5 text-xs text-fg">
        {printers.length === 0 && <option value="">No printers</option>}
        {printers.map((printer) => (
          <option key={printer.id} value={printer.id}>
            {printer.name}{printer.maintenance_flag ? " (locked)" : ""}
          </option>
        ))}
      </select>
    </label>
  );
}

function PresetButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="rounded border border-border bg-bg/40 px-2 py-1 text-xs font-medium text-muted hover:bg-surface2 hover:text-fg">
      {label}
    </button>
  );
}

function StatusPill({ tone, label }: { tone: "green" | "cyan" | "amber" | "red" | "muted"; label: string }) {
  const cls = {
    green: "border-accent-green/40 bg-accent-green/10 text-accent-green",
    cyan: "border-accent-cyan/40 bg-accent-cyan/10 text-accent-cyan",
    amber: "border-accent-amber/40 bg-accent-amber/10 text-accent-amber",
    red: "border-accent-red/40 bg-accent-red/10 text-accent-red",
    muted: "border-border bg-surface2 text-muted",
  }[tone];
  return <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${cls}`}>{label}</span>;
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="flex h-full min-h-[120px] flex-col items-center justify-center gap-1 text-center text-xs">
      <div className="font-semibold text-fg">{title}</div>
      <div className="max-w-[320px] text-muted">{detail}</div>
    </div>
  );
}

function BackendOfflineBanner({
  refreshing,
  failures,
  onRetry,
}: {
  refreshing: boolean;
  failures: number;
  onRetry: () => void;
}) {
  return (
    <section
      data-testid="operator-backend-offline-banner"
      className="rounded border border-accent-amber/60 bg-accent-amber/10 px-3 py-2 text-xs text-accent-amber"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span>
          <strong>Local Hermes3D API is not responding.</strong> Cards are waiting on{" "}
          <span className="font-mono">{LIVE_BASE_URL}</span>; no dashboard data is being faked.
        </span>
        <button
          type="button"
          onClick={onRetry}
          className="rounded border border-accent-amber/50 px-2 py-1 font-semibold hover:bg-accent-amber/15"
        >
          {refreshing ? "Retrying" : `Retry (${failures})`}
        </button>
      </div>
    </section>
  );
}

function BackendPartialBanner({
  refreshing,
  failures,
  onRetry,
}: {
  refreshing: boolean;
  failures: WorkbenchEndpointFailure[];
  onRetry: () => void;
}) {
  const visibleFailures = failures.slice(0, 4);
  const extra = failures.length - visibleFailures.length;
  return (
    <section
      data-testid="operator-backend-partial-banner"
      className="rounded border border-accent-cyan/50 bg-accent-cyan/10 px-3 py-2 text-xs text-accent-cyan"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span>
          <strong>Local Hermes3D API is reachable.</strong> Some dashboard endpoints are slow or failing:{" "}
          <span className="font-mono">
            {visibleFailures.map((failure) => `${failure.label}: ${failure.reason}`).join(" · ")}
            {extra > 0 ? ` · +${extra} more` : ""}
          </span>
        </span>
        <button
          type="button"
          onClick={onRetry}
          className="rounded border border-accent-cyan/50 px-2 py-1 font-semibold hover:bg-accent-cyan/15"
        >
          {refreshing ? "Checking" : "Retry"}
        </button>
      </div>
    </section>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[90px_minmax(0,1fr)] gap-2">
      <span className="text-muted">{label}</span>
      <span className="truncate font-mono text-fg" title={value}>{value}</span>
    </div>
  );
}

async function fetchWorkbenchHealth(): Promise<WorkbenchHealth> {
  const response = await fetch(`${LIVE_BASE_URL}/health`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok || !isRecord(payload) || typeof payload.status !== "string") {
    throw new Error(`HTTP ${response.status}`);
  }
  return {
    status: payload.status,
    service: typeof payload.service === "string" ? payload.service : undefined,
  };
}

async function fetchCameras(): Promise<CameraFeed[]> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/observe/cameras`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    return response.ok && Array.isArray(payload) ? payload.filter(isCameraFeed) : [];
  } catch {
    return [];
  }
}

async function fetchObserveStatus(): Promise<ObserveStatusResponse> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/observe/status`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok || !isRecord(payload) || !Array.isArray(payload.cameras)) {
      return { cameras: [], online: 0, total: 0 };
    }
    return {
      cameras: payload.cameras.filter(isCameraStatus),
      online: numberValue(payload.online),
      total: numberValue(payload.total),
    };
  } catch {
    return { cameras: [], online: 0, total: 0 };
  }
}

async function fetchGen3DTemplates(): Promise<Gen3DTemplate[]> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/gen3d/templates`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    return response.ok && Array.isArray(payload) ? payload.filter(isGen3DTemplate) : [];
  } catch {
    return [];
  }
}

async function fetchGen3DProviders(): Promise<Gen3DProvider[]> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/gen3d/providers`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    return response.ok && Array.isArray(payload) ? payload.filter(isGen3DProvider) : [];
  } catch {
    return [];
  }
}

async function fetchSlicerDesktopApps(): Promise<SlicerDesktopApp[]> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/slicer/apps`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok || !isRecord(payload) || !Array.isArray(payload.apps)) return [];
    const parsed = payload.apps.filter(isRecord).map(parseSlicerDesktopApp).filter((app): app is SlicerDesktopApp => Boolean(app));
    return [...parsed].sort((a, b) => SLICER_APP_ORDER.indexOf(a.id) - SLICER_APP_ORDER.indexOf(b.id));
  } catch {
    return [];
  }
}

async function launchSlicerDesktopApp(moduleId: SlicerModuleId): Promise<SlicerLaunchResult> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/slicer/apps/${moduleId}/launch`, {
      method: "POST",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok || !isRecord(payload)) {
      return { accepted: false, status: "blocked", reason: summary(payload, `HTTP ${response.status}`) };
    }
    return parseSlicerLaunchResult(payload);
  } catch (error) {
    return { accepted: false, status: "error", reason: errorMessage(error) };
  }
}

async function focusSlicerDesktopApp(moduleId: SlicerModuleId): Promise<SlicerLaunchResult> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/slicer/apps/${moduleId}/window/focus`, {
      method: "POST",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok || !isRecord(payload)) {
      return { accepted: false, status: "blocked", reason: summary(payload, `HTTP ${response.status}`) };
    }
    return parseSlicerLaunchResult(payload);
  } catch (error) {
    return { accepted: false, status: "error", reason: errorMessage(error) };
  }
}

async function sendSlicerWindowInput(moduleId: SlicerModuleId, action: "click" | "wheel" | "key", body: Record<string, unknown>): Promise<WindowInputResult> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/slicer/apps/${moduleId}/window/${action}`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify(body),
    });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok || !isRecord(payload)) {
      return { accepted: false, status: "blocked", reason: summary(payload, `HTTP ${response.status}`) };
    }
    return parseWindowInputResult(payload);
  } catch (error) {
    return { accepted: false, status: "error", reason: errorMessage(error) };
  }
}

async function fetchModelerApps(): Promise<ModelerApp[]> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/design/modeler/apps`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok || !isRecord(payload) || !Array.isArray(payload.apps)) return [];
    const parsed = payload.apps.filter(isRecord).map(parseModelerApp).filter((app): app is ModelerApp => Boolean(app));
    return [...parsed].sort((a, b) => MODELER_APP_ORDER.indexOf(a.id) - MODELER_APP_ORDER.indexOf(b.id));
  } catch {
    return [];
  }
}

async function sendModelerWindowInput(appId: string, action: "click" | "wheel" | "key", body: Record<string, unknown>): Promise<WindowInputResult> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/design/modeler/apps/${encodeURIComponent(appId)}/window/${action}`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify(body),
    });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok || !isRecord(payload)) {
      return { accepted: false, status: "blocked", reason: summary(payload, `HTTP ${response.status}`) };
    }
    return parseWindowInputResult(payload);
  } catch (error) {
    return { accepted: false, status: "error", reason: errorMessage(error) };
  }
}

async function launchModelerApp(appId: string): Promise<ModelerLaunchResult> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/design/modeler/apps/${encodeURIComponent(appId)}/launch`, {
      method: "POST",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok || !isRecord(payload)) {
      return { accepted: false, status: "blocked", reason: summary(payload, `HTTP ${response.status}`) };
    }
    return parseModelerLaunchResult(payload);
  } catch (error) {
    return { accepted: false, status: "error", reason: errorMessage(error) };
  }
}

async function focusModelerApp(appId: string): Promise<ModelerLaunchResult> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/design/modeler/apps/${encodeURIComponent(appId)}/window/focus`, {
      method: "POST",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok || !isRecord(payload)) {
      return { accepted: false, status: "blocked", reason: summary(payload, `HTTP ${response.status}`) };
    }
    return parseModelerLaunchResult(payload);
  } catch (error) {
    return { accepted: false, status: "error", reason: errorMessage(error) };
  }
}

function workbenchStorageKey(baseKey: string, modeId: WorkbenchModeId): string {
  return modeId === "advanced" ? baseKey : `${baseKey}.${modeId}`;
}

function fallbackWorkbenchLayout(preset?: LayoutPreset): WorkbenchLayout {
  const order = preset ? [...PRESET_ORDERS[preset]] : [...DEFAULT_WIDGET_ORDER];
  const sizes = { ...DEFAULT_WIDGET_SIZES };
  if (preset === "monitoring") {
    sizes.cameras = "hero";
    sizes.printerConsole = "hero";
    sizes.jobs = "wide";
  }
  if (preset === "modeling") {
    sizes.action = "hero";
    sizes.modeler = "wide";
    sizes.slicerApps = "wide";
    sizes.slicer = "wide";
  }
  if (preset === "software") {
    sizes.cameras = "wide";
    sizes.slicerApps = "hero";
    sizes.modeler = "hero";
    sizes.printerConsole = "wide";
  }
  return { order, sizes };
}

function readWorkbenchLayout(storageKey = WORKBENCH_LAYOUT_KEY, preset?: LayoutPreset): WorkbenchLayout {
  const fallback = fallbackWorkbenchLayout(preset);
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(storageKey);
    const parsed = raw ? JSON.parse(raw) : null;
    if (!isRecord(parsed) || parsed.version !== WORKBENCH_LAYOUT_VERSION) return fallback;
    const order = Array.isArray(parsed.order) ? cleanWidgetOrder(parsed.order, false) : fallback.order;
    const sizes = isRecord(parsed.sizes) ? cleanWidgetSizes(parsed.sizes) : fallback.sizes;
    return { order: order.length > 0 ? order : fallback.order, sizes };
  } catch {
    return fallback;
  }
}

function writeWorkbenchLayout(layout: WorkbenchLayout, storageKey = WORKBENCH_LAYOUT_KEY) {
  try {
    window.localStorage.setItem(
      storageKey,
      JSON.stringify({
        version: WORKBENCH_LAYOUT_VERSION,
        order: cleanWidgetOrder(layout.order, false),
        sizes: cleanWidgetSizes(layout.sizes),
      }),
    );
  } catch {
    /* local layout persistence is best-effort */
  }
}

function readSavedLayouts(storageKey = WORKBENCH_SAVED_LAYOUTS_KEY): SavedWorkbenchLayout[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(storageKey);
    const parsed = raw ? JSON.parse(raw) : null;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isSavedWorkbenchLayout).map((layout) => ({
      name: layout.name,
      savedAt: layout.savedAt,
      order: cleanWidgetOrder(layout.order, false),
      sizes: cleanWidgetSizes(layout.sizes),
    }));
  } catch {
    return [];
  }
}

function writeSavedLayouts(layouts: SavedWorkbenchLayout[], storageKey = WORKBENCH_SAVED_LAYOUTS_KEY) {
  try {
    window.localStorage.setItem(storageKey, JSON.stringify(layouts));
  } catch {
    /* best-effort saved layouts */
  }
}

function cleanWidgetOrder(values: unknown[], includeMissing: boolean): WorkbenchWidgetId[] {
  const clean = values.filter((item): item is WorkbenchWidgetId => isWorkbenchWidgetId(item));
  const unique = clean.filter((item, index) => clean.indexOf(item) === index);
  if (!includeMissing) return unique;
  return [...unique, ...DEFAULT_WIDGET_ORDER.filter((item) => !unique.includes(item))];
}

function cleanWidgetSizes(value: Partial<Record<WorkbenchWidgetId, unknown>>): Record<WorkbenchWidgetId, WidgetSize> {
  const next = { ...DEFAULT_WIDGET_SIZES };
  for (const widget of ALL_WIDGETS) {
    const raw = value[widget];
    if (isWidgetSize(raw)) next[widget] = raw;
  }
  return next;
}

function readActionTab(storageKey = WORKBENCH_ACTION_TAB_KEY, fallback: ActionTab = "model"): ActionTab {
  if (typeof window === "undefined") return fallback;
  const raw = window.localStorage.getItem(storageKey);
  if (raw === "console") return fallback === "console" ? "console" : "model";
  return isActionTab(raw) ? raw : fallback;
}

function writeActionTab(tab: ActionTab, storageKey = WORKBENCH_ACTION_TAB_KEY) {
  try {
    window.localStorage.setItem(storageKey, tab);
  } catch {
    /* best-effort */
  }
}

function isLiveWorkbenchPrinter(printer: Printer): boolean {
  return !printer.maintenance_flag
    && printer.status !== "disabled"
    && printer.status !== "maintenance";
}

function preferredPrinter(printers: Printer[]): Printer | null {
  return (
    printers.find((printer) => printer.current_job)
    ?? printers.find((printer) => printer.ip === "192.168.0.11" || printer.id === "flsun_t1_b")
    ?? printers.find((printer) => printer.write_enabled !== false && !printer.maintenance_flag)
    ?? printers[0]
    ?? null
  );
}

function printerWebConsoleUrl(printer: Printer | null): string {
  if (!printer) return "";
  const raw = printer.moonraker_url ?? (printer.ip ? `http://${printer.ip}` : "");
  if (!raw) return "";
  try {
    const url = new URL(raw);
    if (url.port === "7125") {
      url.port = "";
    }
    url.pathname = "/";
    url.search = "";
    url.hash = "";
    return url.toString().replace(/\/$/, "");
  } catch {
    return raw;
  }
}

function printerMoonrakerApiUrl(printer: Printer | null): string {
  if (!printer?.ip) return "";
  return `http://${printer.ip}:7125`;
}

function dashboardCameraImageStyle(settings: CameraViewSettings): CSSProperties {
  return {
    objectFit: settings.fit,
    objectPosition: `${settings.focus_x}% ${settings.focus_y}%`,
    transform: `rotate(${settings.rotate_deg}deg) scaleX(${settings.mirror_x ? -1 : 1}) scaleY(${settings.mirror_y ? -1 : 1}) scale(${settings.zoom})`,
    transformOrigin: "center center",
    filter: `brightness(${settings.brightness}%) contrast(${settings.contrast}%) saturate(${settings.saturation}%)`,
  };
}

function cameraUrl(path: string, cacheKey?: number | null): string {
  const url = path.startsWith("http://") || path.startsWith("https://") ? path : `${LIVE_BASE_URL}${path}`;
  if (cacheKey == null) return url;
  return `${url}${url.includes("?") ? "&" : "?"}t=${cacheKey}`;
}

function desktopWindowPreviewUrl(path: string, previewKey: number, fps: number): string {
  const url = path.startsWith("http://") || path.startsWith("https://") ? path : `${LIVE_BASE_URL}${path}`;
  const separator = url.includes("?") ? "&" : "?";
  if (url.includes("/stream.mjpeg")) {
    return `${url}${separator}fps=${fps}`;
  }
  return `${url}${separator}t=${previewKey}`;
}

function sourceSupportLabel(source: SourceToolSupport | undefined): string {
  if (!source) return "-";
  if (source.source_path) return source.source_path;
  return source.source_status.replace("_", " ");
}

function consoleFrameUrl(path: string, reloadKey: number): string {
  try {
    const url = new URL(path);
    url.searchParams.set("hermesReload", String(reloadKey));
    return url.toString();
  } catch {
    return `${path}${path.includes("?") ? "&" : "?"}hermesReload=${reloadKey}`;
  }
}

function withWorkbenchTimeout<T>(
  label: string,
  promise: Promise<T>,
  fallback: T,
  timeoutMs = WORKBENCH_REQUEST_TIMEOUT_MS,
): Promise<{ label: string; value: T; failed: boolean; reason?: string }> {
  return new Promise((resolve) => {
    let settled = false;
    const finish = (value: T, failed: boolean, reason?: string) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeout);
      resolve({ label, value, failed, reason });
    };
    const timeout = window.setTimeout(() => finish(fallback, true, `timed out after ${timeoutMs}ms`), timeoutMs);
    promise
      .then((value) => finish(value, false))
      .catch((error: unknown) => finish(fallback, true, errorMessage(error)));
  });
}

function parseArtifactId(payload: unknown): string | null {
  return isRecord(payload) && typeof payload.id === "string" ? payload.id : null;
}

function parseGeneratedModel(payload: unknown): GeneratedModelResult | null {
  if (!isRecord(payload) || typeof payload.job_id !== "string" || !isRecord(payload.artifact)) return null;
  const artifact = payload.artifact;
  if (typeof artifact.label !== "string" || typeof artifact.file_path !== "string") return null;
  const package3mf = isRecord(payload.package_3mf) ? payload.package_3mf : null;
  return {
    jobId: payload.job_id,
    template: typeof payload.template === "string" ? payload.template : "local_template",
    artifactLabel: artifact.label,
    artifactPath: artifact.file_path,
    artifactSize: typeof artifact.file_size === "number" ? artifact.file_size : 0,
    packageLabel: package3mf && typeof package3mf.label === "string" ? package3mf.label : undefined,
    packagePath: package3mf && typeof package3mf.file_path === "string" ? package3mf.file_path : undefined,
    packageSize: package3mf && typeof package3mf.file_size === "number" ? package3mf.file_size : undefined,
    truthGate: isRecord(payload.truth_gate) && typeof payload.truth_gate.status === "string" ? payload.truth_gate.status : undefined,
  };
}

function parseSlicerDesktopApp(payload: Record<string, unknown>): SlicerDesktopApp | null {
  const id = payload.id === "prusaslicer" || payload.id === "flsun_slicer" || payload.id === "orcaslicer" ? payload.id : null;
  const moduleId = payload.module_id === "prusaslicer" || payload.module_id === "flsun_slicer" || payload.module_id === "orcaslicer" ? payload.module_id : id;
  if (!id || !moduleId) return null;
  return {
    id,
    module_id: moduleId,
    label: stringOr(payload.label, SLICER_CARD_CONFIGS[widgetForSlicerModule(moduleId)].title),
    status: stringOr(payload.status, "unknown"),
    detected: payload.detected === true,
    path: stringOr(payload.path, SLICER_CARD_CONFIGS[widgetForSlicerModule(moduleId)].primaryPath),
    path_source: stringOr(payload.path_source, "default"),
    user_path: typeof payload.user_path === "string" ? payload.user_path : null,
    default_path: stringOr(payload.default_path, SLICER_CARD_CONFIGS[widgetForSlicerModule(moduleId)].primaryPath),
    candidates: Array.isArray(payload.candidates) ? payload.candidates.filter(isRecord).map(parseSlicerDesktopCandidate) : [],
    launch_supported: payload.launch_supported === true,
    window: isRecord(payload.window) ? parseSlicerWindow(payload.window) : { available: false, status: "unknown" },
    window_available: payload.window_available === true,
    window_preview_url: stringOr(payload.window_preview_url, `/api/slicer/apps/${id}/window/screenshot.png`),
    window_stream_url: stringOrUndefined(payload.window_stream_url),
    source_support: isRecord(payload.source_support) ? parseSourceToolSupport(payload.source_support) : undefined,
    proof_gate_version: stringOr(payload.proof_gate_version, "desktop-slicer-launcher-v1"),
    safety: stringOr(payload.safety, "Launches the slicer desktop program only."),
  };
}

function parseSlicerWindow(payload: Record<string, unknown>): SlicerWindowRecord {
  return {
    available: payload.available === true,
    status: stringOr(payload.status, "unknown"),
    reason: stringOrUndefined(payload.reason),
    title: stringOrUndefined(payload.title),
    process_id: typeof payload.process_id === "number" ? payload.process_id : undefined,
    process_name: stringOrUndefined(payload.process_name),
    process_path: stringOrUndefined(payload.process_path),
    preview_url: stringOrUndefined(payload.preview_url),
    stream_url: stringOrUndefined(payload.stream_url),
  };
}

function parseSlicerDesktopCandidate(payload: Record<string, unknown>): SlicerDesktopCandidate {
  return {
    source: stringOr(payload.source, "known"),
    path: stringOr(payload.path, ""),
    exists: payload.exists === true,
    is_executable: payload.is_executable === true,
  };
}

function parseSlicerLaunchResult(payload: Record<string, unknown>): SlicerLaunchResult {
  const app = isRecord(payload.app) ? parseSlicerDesktopApp(payload.app) ?? undefined : undefined;
  return {
    accepted: payload.accepted === true,
    status: stringOr(payload.status, "unknown"),
    pid: typeof payload.pid === "number" ? payload.pid : undefined,
    reason: stringOrUndefined(payload.reason ?? payload.detail),
    proof_event_id: stringOrUndefined(payload.proof_event_id),
    app,
  };
}

function parseModelerApp(payload: Record<string, unknown>): ModelerApp | null {
  if (typeof payload.id !== "string") return null;
  return {
    id: payload.id,
    label: stringOr(payload.label, payload.id),
    kind: stringOr(payload.kind, "desktop_modeler"),
    status: stringOr(payload.status, "unknown"),
    detected: payload.detected === true,
    path: stringOr(payload.path, ""),
    path_source: stringOr(payload.path_source, "default"),
    default_path: stringOr(payload.default_path, ""),
    candidates: Array.isArray(payload.candidates) ? payload.candidates.filter(isRecord).map(parseSlicerDesktopCandidate) : [],
    launch_supported: payload.launch_supported === true,
    window: isRecord(payload.window) ? parseSlicerWindow(payload.window) : { available: false, status: "unknown" },
    window_available: payload.window_available === true,
    window_preview_url: stringOr(payload.window_preview_url, ""),
    window_stream_url: stringOrUndefined(payload.window_stream_url),
    source_support: isRecord(payload.source_support) ? parseSourceToolSupport(payload.source_support) : undefined,
    safety: stringOr(payload.safety, "Shows a local modeler surface only."),
  };
}

function parseSourceToolSupport(payload: Record<string, unknown>): SourceToolSupport {
  return {
    tool_id: stringOr(payload.tool_id, ""),
    label: stringOr(payload.label, ""),
    supported_type: stringOr(payload.supported_type, "unregistered"),
    family: stringOrUndefined(payload.family),
    source_status: stringOr(payload.source_status, "unknown"),
    source_found: payload.source_found === true,
    source_path: stringOrUndefined(payload.source_path),
    version_tag: stringOrUndefined(payload.version_tag),
    upstream_url: stringOrUndefined(payload.upstream_url),
    support_modes: Array.isArray(payload.support_modes) ? payload.support_modes.map((item) => String(item)) : [],
    ui_strategy: stringOr(payload.ui_strategy, "unknown"),
    notes: stringOrUndefined(payload.notes),
  };
}

function parseModelerLaunchResult(payload: Record<string, unknown>): ModelerLaunchResult {
  const app = isRecord(payload.app) ? parseModelerApp(payload.app) ?? undefined : undefined;
  return {
    accepted: payload.accepted === true,
    status: stringOr(payload.status, "unknown"),
    pid: typeof payload.pid === "number" ? payload.pid : undefined,
    reason: stringOrUndefined(payload.reason ?? payload.detail),
    proof_event_id: stringOrUndefined(payload.proof_event_id),
    app,
  };
}

function parseWindowInputResult(payload: Record<string, unknown>): WindowInputResult {
  return {
    accepted: payload.accepted === true,
    status: stringOr(payload.status, "unknown"),
    reason: stringOrUndefined(payload.reason ?? payload.detail),
  };
}

function widgetForSlicerModule(moduleId: SlicerModuleId): SlicerWidgetId {
  if (moduleId === "prusaslicer") return "prusaSlicer";
  if (moduleId === "flsun_slicer") return "flsunSlicer";
  return "orcaSlicer";
}

function stringOr(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function stringOrUndefined(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function summary(payload: unknown, fallback: string): string {
  if (!isRecord(payload)) return fallback || "No response body.";
  if (typeof payload.detail === "string") return payload.detail;
  if (isRecord(payload.detail)) return String(payload.detail.reason ?? payload.detail.message ?? payload.detail.status ?? fallback);
  return String(payload.reason ?? payload.message ?? payload.status ?? fallback);
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function isWorkbenchWidgetId(value: unknown): value is WorkbenchWidgetId {
  return value === "action"
    || value === "cameras"
    || value === "printerConsole"
    || value === "jobs"
    || value === "agents"
    || value === "modeler"
    || value === "slicer"
    || value === "slicerApps"
    || isSlicerWidgetId(value);
}

function isSlicerWidgetId(value: unknown): value is SlicerWidgetId {
  return value === "prusaSlicer" || value === "flsunSlicer" || value === "orcaSlicer";
}

function isWidgetSize(value: unknown): value is WidgetSize {
  return value === "compact" || value === "standard" || value === "wide" || value === "tall" || value === "hero" || value === "full";
}

function isActionTab(value: unknown): value is ActionTab {
  return value === "model" || value === "slice" || value === "printer" || value === "console";
}

function isSavedWorkbenchLayout(value: unknown): value is SavedWorkbenchLayout {
  return isRecord(value)
    && typeof value.name === "string"
    && typeof value.savedAt === "string"
    && Array.isArray(value.order)
    && isRecord(value.sizes);
}

function isCameraFeed(value: unknown): value is CameraFeed {
  return isRecord(value) && typeof value.printer_id === "string" && typeof value.printer_name === "string" && typeof value.stream_url === "string";
}

function isCameraStatus(value: unknown): value is CameraStatus {
  return isRecord(value) && typeof value.printer_id === "string" && typeof value.printer_name === "string" && typeof value.health === "string";
}

function isGen3DTemplate(value: unknown): value is Gen3DTemplate {
  return isRecord(value) && typeof value.id === "string" && typeof value.name === "string";
}

function isGen3DProvider(value: unknown): value is Gen3DProvider {
  return isRecord(value) && typeof value.provider_id === "string" && typeof value.label === "string" && typeof value.readiness === "string";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value));
}
