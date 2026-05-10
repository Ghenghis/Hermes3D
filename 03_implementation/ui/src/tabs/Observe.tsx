import {
  Activity,
  Camera,
  FlipHorizontal,
  FlipVertical,
  Lock,
  Maximize2,
  Minimize2,
  RefreshCw,
  RotateCcw,
  RotateCw,
  SlidersHorizontal,
  Timer,
  VideoOff,
  Wifi,
  WifiOff,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from "react";
import { adapters } from "../api/adapters";
import { useStore } from "../app/store";
import type {
  BuildPlateClearance,
  CameraFeed,
  CameraHealth,
  CameraStatus,
  CameraViewSettings,
  ObserveStatusResponse,
} from "../types/observe";

/** Configurable auto-refresh interval for camera status polling (ms). */
const AUTO_REFRESH_INTERVAL_MS = 5_000;

/** Exponential backoff for feed reconnect attempts. */
const BACKOFF_BASE_MS = 1_000;
const BACKOFF_MAX_MS = 30_000;

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

const DEFAULT_VIEW_SETTINGS: CameraViewSettings = {
  rotate_deg: 0,
  mirror_x: false,
  mirror_y: false,
  zoom: 1,
  focus_x: 50,
  focus_y: 50,
  brightness: 100,
  contrast: 100,
  saturation: 100,
  fit: "cover",
  feed_mode: "stream",
  card_size: "standard",
  review_overlay: "none",
};

export function ObserveTab() {
  const setActiveTabId = useStore((state) => state.setActiveTabId);
  const [pluginStatus, setPluginStatus] = useState<{ status: string; reason: string }>({
    status: "READY",
    reason: "Checking Camera Observer status.",
  });
  const [cameras, setCameras] = useState<CameraFeed[]>([]);
  const [feedState, setFeedState] = useState<Record<string, "loading" | "online" | "error" | "reconnecting">>({});
  /** Per-camera retry attempt count for exponential backoff. */
  const retryCountRef = useRef<Record<string, number>>({});
  const retryTimerRef = useRef<Record<string, ReturnType<typeof window.setTimeout>>>({});
  const [cameraMessage, setCameraMessage] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [undockedCameraId, setUndockedCameraId] = useState<string | null>(null);
  const [controlsOpen, setControlsOpen] = useState<Record<string, boolean>>({});
  const [visibleCameraIds, setVisibleCameraIds] = useState<Record<string, boolean>>({});
  const [viewMode, setViewMode] = useState<"all" | "selected" | "one" | "two" | "three">("all");
  /** Live status from /api/observe/status — fps estimates + online/offline per camera. */
  const [cameraStatus, setCameraStatus] = useState<Record<string, CameraStatus>>({});
  /** Auto-refresh interval in ms; user can adjust via UI. */
  const [autoRefreshMs, setAutoRefreshMs] = useState(AUTO_REFRESH_INTERVAL_MS);

  const loadCameras = useCallback(async () => {
    let rows: CameraFeed[] = [];
    try {
      rows = await fetchCameras();
      setCameraMessage(null);
    } catch (error) {
      setCameraMessage(`Blocked: ${errorMessage(error)}`);
      setCameras([]);
      setFeedState({});
      return [];
    }
    setCameras(rows);
    setFeedState(initialFeedState(rows));
    setRefreshNonce((current) => current + 1);
    setVisibleCameraIds((current) => {
      const next = Object.fromEntries(rows.map((camera) => [camera.printer_id, current[camera.printer_id] ?? true]));
      return next;
    });
    return rows;
  }, []);

  /** Fetch /api/observe/status and update cameraStatus map. */
  const loadStatus = useCallback(async () => {
    try {
      const data = await fetchObserveStatus();
      setCameraStatus(
        Object.fromEntries(data.cameras.map((s) => [s.printer_id, s])),
      );
    } catch {
      // Status is best-effort; don't surface errors here
    }
  }, []);

  /**
   * Handle a feed error for a specific camera with exponential backoff.
   * Transitions: error → reconnecting → (retry) → loading → online | error.
   * Never sends control commands — only updates UI state and resets refreshNonce.
   */
  const handleFeedError = useCallback((printerId: string) => {
    setFeedState((current) => ({ ...current, [printerId]: "reconnecting" }));
    const attempt = (retryCountRef.current[printerId] ?? 0) + 1;
    retryCountRef.current[printerId] = attempt;
    const delay = Math.min(BACKOFF_BASE_MS * Math.pow(2, attempt - 1), BACKOFF_MAX_MS);
    // Clear any pending retry for this camera
    const pending = retryTimerRef.current[printerId];
    if (pending !== undefined) {
      window.clearTimeout(pending);
    }
    retryTimerRef.current[printerId] = window.setTimeout(() => {
      setFeedState((current) => ({ ...current, [printerId]: "loading" }));
      setRefreshNonce((n) => n + 1);
    }, delay);
  }, []);

  /** Reset retry counter when a feed comes online. */
  const handleFeedOnline = useCallback((printerId: string) => {
    retryCountRef.current[printerId] = 0;
    const pending = retryTimerRef.current[printerId];
    if (pending !== undefined) {
      window.clearTimeout(pending);
      delete retryTimerRef.current[printerId];
    }
    setFeedState((current) => ({ ...current, [printerId]: "online" }));
  }, []);

  const handleRefresh = useCallback(async () => {
    const startedAt = window.performance.now();
    setIsRefreshing(true);
    setCameraMessage("Refreshing configured live camera feeds.");
    try {
      const rows = await loadCameras();
      await loadStatus();
      const elapsed = window.performance.now() - startedAt;
      if (elapsed < 650) {
        await new Promise((resolve) => window.setTimeout(resolve, 650 - elapsed));
      }
      if (rows.length > 0) {
        const configuredCount = rows.filter((camera) => camera.camera_url).length;
        setCameraMessage(`Camera feeds refreshed: ${configuredCount}/${rows.length} configured feeds.`);
      } else {
        setCameraMessage("Refresh completed: no camera rows returned by the live observe API.");
      }
    } finally {
      setIsRefreshing(false);
    }
  }, [loadCameras, loadStatus]);

  useEffect(() => {
    let mounted = true;
    void adapters.getCameraObserverStatus().then(async (next) => {
      if (!mounted) {
        return;
      }
      setPluginStatus(next);
      if (isObserverAvailable(next.status)) {
        const rows = await loadCameras();
        if (mounted) {
          setCameras(rows);
          // Initial status fetch for fps/online indicators
          void loadStatus();
        }
      }
      await adapters.emitProofEvent(
        isObserverAvailable(next.status) ? "observe.unlocked" : "observe.disabled_state.displayed",
        { reason: next.reason, plugin_status: next.status },
      );
    });
    return () => {
      mounted = false;
    };
  }, [loadCameras, loadStatus]);

  /** Auto-refresh: poll /api/observe/status on configurable interval. */
  useEffect(() => {
    if (autoRefreshMs <= 0) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadStatus();
    }, autoRefreshMs);
    return () => {
      window.clearInterval(timer);
    };
  }, [loadStatus, autoRefreshMs]);

  /** Cleanup retry timers on unmount. */
  useEffect(() => {
    return () => {
      for (const timer of Object.values(retryTimerRef.current)) {
        window.clearTimeout(timer);
      }
    };
  }, []);

  const undockedCamera = useMemo(
    () => cameras.find((camera) => camera.printer_id === undockedCameraId) ?? null,
    [cameras, undockedCameraId],
  );
  const displayedCameras = useMemo(
    () => cameraRowsForMode(cameras, visibleCameraIds, viewMode),
    [cameras, viewMode, visibleCameraIds],
  );

  if (!isObserverAvailable(pluginStatus.status)) {
    return (
      <div data-testid="observe-root" className="flex h-full min-h-0 items-center justify-center rounded-card border border-border bg-surface p-6">
        <section className="max-w-xl text-center">
          <h2 className="text-base font-semibold text-fg">Observe</h2>
          <div className="mx-auto mt-3 inline-flex rounded bg-surface2 px-3 py-1 text-xs font-semibold text-muted">DISABLED</div>
          <p className="mt-4 text-sm text-muted">{pluginStatus.reason}</p>
          <button type="button" onClick={() => setActiveTabId("plugins")} className="mt-5 rounded bg-accent-blue px-4 py-2 text-sm font-semibold text-bg">
            Go to Plugins
          </button>
        </section>
      </div>
    );
  }

  const onlineCount = Object.values(cameraStatus).filter((s) => s.health === "reachable").length;
  const totalStatusCount = Object.keys(cameraStatus).length;

  /**
   * ARIA live announcement for camera state transitions.
   *
   * Built from the most recently changed fields the operator should hear about:
   * online/total count, refresh state, plate clearance changes, and any backend
   * error stored in cameraMessage. The wrapping div uses role="status" with
   * aria-live="polite" so screen readers get the update without interrupting
   * the user (W3C WAI-ARIA Live Regions guidance + WCAG 2.1 SC 4.1.3).
   */
  const ariaAnnouncement = (() => {
    if (cameraMessage) return cameraMessage;
    if (isRefreshing) return "Refreshing live camera feeds.";
    if (totalStatusCount === 0) return "Camera fleet status loading.";
    return `${onlineCount} of ${totalStatusCount} camera feeds online.`;
  })();

  return (
    <div data-testid="observe-root" className="grid h-full min-h-0 grid-rows-[auto_auto_minmax(0,1fr)_auto] gap-2.5 rounded-card border border-border bg-surface p-3 text-fg">
      {/* ARIA live region — politely announces camera count / refresh / error changes. */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
        data-testid="observe-aria-live"
      >
        {ariaAnnouncement}
      </div>
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-[13px] font-semibold">Camera Observer</h2>
          <p className="truncate text-[11px] text-muted">{pluginStatus.reason}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {totalStatusCount > 0 && (
            <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-semibold ${onlineCount === totalStatusCount ? "bg-green-900/40 text-green-300" : "bg-amber-900/40 text-amber-300"}`}>
              {onlineCount === totalStatusCount ? <Wifi size={11} /> : <WifiOff size={11} />}
              {onlineCount}/{totalStatusCount} online
            </span>
          )}
          <div className="flex items-center gap-1 text-[11px] text-muted">
            <Timer size={11} />
            <select
              value={autoRefreshMs}
              onChange={(e) => setAutoRefreshMs(Number(e.currentTarget.value))}
              className="rounded border border-border bg-bg px-1 py-0.5 text-[10px] text-fg"
              title="Auto-refresh interval for camera status"
            >
              <option value={0}>off</option>
              <option value={3000}>3 s</option>
              <option value={5000}>5 s</option>
              <option value={10000}>10 s</option>
              <option value={30000}>30 s</option>
            </select>
          </div>
          <button
            type="button"
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              void handleRefresh();
            }}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 text-xs text-fg hover:border-accent-blue disabled:cursor-wait disabled:opacity-70"
          >
            <RefreshCw size={13} className={isRefreshing ? "animate-spin" : ""} />
            {isRefreshing ? "Refreshing" : "Refresh"}
          </button>
        </div>
      </header>

      <div className="flex flex-wrap items-center justify-between gap-2 rounded border border-border bg-bg/30 p-1.5 text-[11px]">
        <div className="flex flex-wrap items-center gap-1.5">
        <span className="mr-1 text-muted">Visible feeds</span>
        {cameras.map((camera) => (
          <button
            key={camera.printer_id}
            type="button"
            onClick={() => setVisibleCameraIds((current) => ({ ...current, [camera.printer_id]: current[camera.printer_id] !== true }))}
            className={`rounded border px-2 py-1 ${visibleCameraIds[camera.printer_id] === true ? "border-accent-cyan bg-cyan-950/50 text-accent-cyan" : "border-border text-muted"}`}
          >
            {camera.printer_name}
          </button>
        ))}
        </div>
        <div className="flex flex-wrap items-center gap-1">
          <span className="mr-1 text-muted">View</span>
          {(["all", "selected", "one", "two", "three"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setViewMode(mode)}
              className={`rounded border px-2 py-1 ${viewMode === mode ? "border-accent-amber bg-amber-950/40 text-accent-amber" : "border-border text-fg"}`}
            >
              {viewModeLabel(mode)}
            </button>
          ))}
        </div>
      </div>

      <div className="grid min-h-0 auto-rows-[minmax(14rem,1fr)] gap-2 overflow-auto lg:grid-cols-2 xl:grid-cols-2 2xl:grid-cols-4">
        {displayedCameras.map((camera) => (
          <CameraCard
            key={camera.printer_id}
            camera={camera}
            feedState={feedState[camera.printer_id] ?? "loading"}
            cameraStatus={cameraStatus[camera.printer_id] ?? null}
            refreshNonce={refreshNonce}
            controlsOpen={controlsOpen[camera.printer_id] === true}
            onToggleControls={() => setControlsOpen((current) => ({ ...current, [camera.printer_id]: current[camera.printer_id] !== true }))}
            onViewChange={(updates) => void updateCameraView(camera.printer_id, updates, setCameras, setCameraMessage)}
            onFeedOnline={() => handleFeedOnline(camera.printer_id)}
            onFeedError={() => handleFeedError(camera.printer_id)}
            onProbe={(printerId) => void probeCamera(printerId, setCameraMessage)}
            onClearPlate={(printerId) => void markPlateClear(printerId, setCameras, setCameraMessage)}
            onUndock={(printerId) => setUndockedCameraId(printerId)}
          />
        ))}
        {cameras.length === 0 && (
          <div className="rounded-card border border-border bg-bg/40 p-3 text-sm text-muted">
            No camera rows returned by the live observe API.
          </div>
        )}
        {cameras.length > 0 && displayedCameras.length === 0 && (
          <div className="rounded-card border border-border bg-bg/40 p-3 text-sm text-muted">
            No selected camera feeds are visible.
          </div>
        )}
      </div>

      {cameraMessage && <div data-testid="observe-status-banner" className="rounded border border-border bg-bg/40 p-2 text-xs text-muted">{cameraMessage}</div>}

      {undockedCamera && (
        <div className="fixed inset-0 z-50 grid bg-bg/85 p-4 backdrop-blur-sm">
          <div className="grid min-h-0 rounded-card border border-border bg-surface shadow-2xl">
            <CameraCard
              camera={undockedCamera}
              feedState={feedState[undockedCamera.printer_id] ?? "loading"}
              cameraStatus={cameraStatus[undockedCamera.printer_id] ?? null}
              refreshNonce={refreshNonce}
              controlsOpen={controlsOpen[undockedCamera.printer_id] !== false}
              undocked
              onToggleControls={() => setControlsOpen((current) => ({
                ...current,
                [undockedCamera.printer_id]: current[undockedCamera.printer_id] === false,
              }))}
              onViewChange={(updates) => void updateCameraView(undockedCamera.printer_id, updates, setCameras, setCameraMessage)}
              onFeedOnline={() => handleFeedOnline(undockedCamera.printer_id)}
              onFeedError={() => handleFeedError(undockedCamera.printer_id)}
              onProbe={(printerId) => void probeCamera(printerId, setCameraMessage)}
              onClearPlate={(printerId) => void markPlateClear(printerId, setCameras, setCameraMessage)}
              onUndock={() => setUndockedCameraId(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function CameraCard({
  camera,
  feedState,
  cameraStatus,
  refreshNonce,
  controlsOpen,
  undocked = false,
  onToggleControls,
  onViewChange,
  onFeedOnline,
  onFeedError,
  onProbe,
  onClearPlate,
  onUndock,
}: {
  camera: CameraFeed;
  feedState: "loading" | "online" | "error" | "reconnecting";
  cameraStatus: CameraStatus | null;
  refreshNonce: number;
  controlsOpen: boolean;
  undocked?: boolean;
  onToggleControls: () => void;
  onViewChange: (updates: Partial<CameraViewSettings>) => void;
  onFeedOnline: () => void;
  onFeedError: () => void;
  onProbe: (printerId: string) => void;
  onClearPlate: (printerId: string) => void;
  onUndock: (printerId: string) => void;
}) {
  const settings = camera.view_settings;
  const [snapshotNonce, setSnapshotNonce] = useState(0);
  const configured = typeof camera.camera_url === "string" && camera.camera_url.length > 0;
  const feedPath = settings.feed_mode === "snapshot" ? camera.snapshot_url : camera.stream_url;
  const nonce = settings.feed_mode === "snapshot" ? snapshotNonce : refreshNonce;
  const feedSrc = configured ? `${LIVE_BASE_URL}${feedPath}?t=${nonce}` : null;
  const status = configured ? feedStateLabel(feedState, camera.health) : "NO FEED";
  const needsClearance = camera.plate_clearance?.state === "needs_clearance";
  const cardSizeClass = undocked ? "h-full" : cardSizeClassName(settings.card_size);
  const cardMinClass = undocked ? "min-h-0" : cardMinHeightClass(settings.card_size);
  const resizeStyle: CSSProperties = undocked ? {} : { resize: "both" };

  // V400 fps indicator — show estimated fps from status probe
  const estimatedFps = cameraStatus?.estimated_fps ?? null;
  const isV400 = camera.camera_kind === "usb_webcam";

  return (
    <section
      className={`grid ${cardMinClass} min-w-[16rem] grid-rows-[auto_minmax(0,1fr)_auto] overflow-hidden rounded-card border border-border bg-bg/45 ${cardSizeClass}`}
      style={resizeStyle}
    >
      <header className="flex items-start justify-between gap-2 border-b border-border p-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <Camera size={14} className={configured ? "text-accent-cyan" : "text-muted"} />
            <span className="truncate text-xs font-semibold text-fg">{camera.printer_name}</span>
            {camera.printer_locked && <Lock size={12} className="shrink-0 text-accent-amber" aria-label="printer actions locked" />}
          </div>
          <div className="mt-0.5 truncate font-mono text-[10px] text-muted">{camera.camera_url ?? camera.camera_note}</div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {/* V400 online/offline status chip */}
          {isV400 && cameraStatus && (
            <span
              className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[9px] font-semibold ${cameraStatus.health === "reachable" ? "bg-green-900/40 text-green-300" : "bg-surface2 text-muted"}`}
              title={`V400 webcam: ${cameraStatus.health}`}
            >
              {cameraStatus.health === "reachable" ? <Wifi size={9} /> : <WifiOff size={9} />}
              {cameraStatus.health === "reachable" ? "V400 LIVE" : "V400 OFFLINE"}
            </span>
          )}
          {/* fps indicator for V400 */}
          {isV400 && estimatedFps !== null && (
            <span className="inline-flex items-center gap-0.5 rounded bg-surface2/80 px-1.5 py-0.5 text-[9px] font-mono text-muted" title="Estimated frame rate">
              <Activity size={9} />
              {estimatedFps} fps
            </span>
          )}
          <span className={statusClass(camera, feedState)}>{status}</span>
          <button type="button" onClick={onToggleControls} className="rounded border border-border p-1 text-muted hover:text-fg" title="Camera display controls">
            <SlidersHorizontal size={13} />
          </button>
          <button
            type="button"
            onClick={() => onUndock(camera.printer_id)}
            className="rounded border border-border p-1 text-muted hover:text-fg"
            title={undocked ? "Dock camera card" : "Undock camera card"}
          >
            {undocked ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>
        </div>
      </header>

      <div className="grid min-h-0 grid-rows-[minmax(0,1fr)_auto]">
        <div className="relative min-h-0 overflow-hidden bg-black">
          {feedSrc ? (
            <>
              <img
                src={feedSrc}
                alt={`${camera.printer_name} live camera feed`}
                className="h-full w-full"
                style={cameraImageStyle(settings)}
                onLoad={onFeedOnline}
                onError={onFeedError}
              />
              <ReviewOverlay mode={settings.review_overlay} />
              {feedState === "loading" && (
                <FeedOverlay icon={<Camera size={24} />} title="Connecting to live camera" detail={camera.camera_kind === "integrated" ? "Integrated camera feed" : "USB webcam feed"} />
              )}
              {feedState === "reconnecting" && (
                <FeedOverlay icon={<RefreshCw size={24} className="animate-spin" />} title="Reconnecting..." detail="Connection lost. Retrying with backoff." />
              )}
              {feedState === "error" && (
                <FeedOverlay icon={<VideoOff size={24} />} title="Camera feed unreachable" detail="The configured URL did not return a browser-readable stream." />
              )}
            </>
          ) : (
            <FeedOverlay
              icon={<VideoOff size={24} />}
              title={camera.camera_kind === "usb_webcam" ? "USB webcam not configured" : "Camera URL missing"}
              detail={camera.camera_note}
            />
          )}
        </div>
        {controlsOpen && (
          <CameraControls
            configured={configured}
            printerId={camera.printer_id}
            settings={settings}
            onViewChange={onViewChange}
            onRefreshSnapshot={() => setSnapshotNonce((current) => current + 1)}
          />
        )}
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border p-2 text-[11px]">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <span className="text-muted">{cameraKindLabel(camera.camera_kind)}</span>
          {camera.printer_locked && <span className="text-accent-amber">printer actions locked</span>}
          {camera.plate_clearance && (
            <span className={needsClearance ? "font-semibold text-accent-amber" : camera.plate_clearance.state === "clear" ? "text-accent-green" : "text-muted"}>
              {plateLabel(camera.plate_clearance)}
            </span>
          )}
        </div>
        <div className="flex gap-1.5">
          <button
            type="button"
            disabled={!needsClearance}
            title={needsClearance ? "Confirm the build plate is clear after visual/camera review." : "No build plate clearance is required."}
            onClick={() => onClearPlate(camera.printer_id)}
            className="rounded border border-border px-2 py-1 text-fg disabled:cursor-not-allowed disabled:opacity-50"
          >
            Mark Clear
          </button>
          <button
            type="button"
            disabled={!configured}
            title={configured ? "Open configured camera URL" : camera.camera_note}
            onClick={() => camera.camera_url && window.open(camera.camera_url, "_blank", "noopener,noreferrer")}
            className="rounded border border-border px-2 py-1 text-fg disabled:cursor-not-allowed disabled:opacity-50"
          >
            Open
          </button>
          <button
            type="button"
            disabled={!configured}
            title={configured ? "Probe the configured camera URL through the backend." : camera.camera_note}
            onClick={() => onProbe(camera.printer_id)}
            className="rounded border border-border px-2 py-1 text-fg disabled:cursor-not-allowed disabled:opacity-50"
          >
            Probe
          </button>
        </div>
      </footer>
    </section>
  );
}

function CameraControls({
  configured,
  printerId,
  settings,
  onViewChange,
  onRefreshSnapshot,
}: {
  configured: boolean;
  printerId: string;
  settings: CameraViewSettings;
  onViewChange: (updates: Partial<CameraViewSettings>) => void;
  onRefreshSnapshot: () => void;
}) {
  const s1Preset = printerId === "flsun_s1";
  return (
    <div className="grid gap-2 border-t border-border bg-surface2/35 p-2 text-[10px] text-muted md:grid-cols-2 xl:grid-cols-3">
      <div className="flex flex-wrap gap-1">
        <IconButton title="Rotate left 90 degrees" onClick={() => onViewChange({ rotate_deg: rotateLeft(settings.rotate_deg) })}>
          <RotateCcw size={13} />
        </IconButton>
        <IconButton title="Rotate right 90 degrees" onClick={() => onViewChange({ rotate_deg: rotateRight(settings.rotate_deg) })}>
          <RotateCw size={13} />
        </IconButton>
        <button type="button" onClick={() => onViewChange({ rotate_deg: rotateHalf(settings.rotate_deg) })} className="rounded border border-border px-2 py-1 text-fg">
          180
        </button>
        <IconButton title="Flip horizontal" active={settings.mirror_x} onClick={() => onViewChange({ mirror_x: !settings.mirror_x })}>
          <FlipHorizontal size={13} />
        </IconButton>
        <IconButton title="Flip vertical" active={settings.mirror_y} onClick={() => onViewChange({ mirror_y: !settings.mirror_y })}>
          <FlipVertical size={13} />
        </IconButton>
        <button type="button" onClick={() => onViewChange({ fit: settings.fit === "cover" ? "contain" : "cover" })} className="rounded border border-border px-2 py-1 text-fg">
          {settings.fit}
        </button>
        <button type="button" onClick={() => onViewChange(defaultViewSettings(printerId))} className="rounded border border-border px-2 py-1 text-fg">
          {s1Preset ? "S1 90" : "reset"}
        </button>
        <IconButton title="Zoom out" onClick={() => onViewChange({ zoom: clamp(settings.zoom - 0.25, 0.5, 4) })}>
          <ZoomOut size={13} />
        </IconButton>
        <button type="button" onClick={() => onViewChange({ zoom: 1 })} className="rounded border border-border px-2 py-1 text-fg">
          1x
        </button>
        <IconButton title="Zoom in" onClick={() => onViewChange({ zoom: clamp(settings.zoom + 0.25, 0.5, 4) })}>
          <ZoomIn size={13} />
        </IconButton>
      </div>
      <div className="flex flex-wrap gap-1">
        <span className="mr-1 self-center text-muted">Size</span>
        {(["compact", "standard", "wide", "large", "full"] as const).map((size) => (
          <button
            key={size}
            type="button"
            onClick={() => onViewChange({ card_size: size })}
            className={`rounded border px-2 py-1 ${settings.card_size === size ? "border-accent-cyan bg-cyan-950/50 text-accent-cyan" : "border-border text-fg"}`}
          >
            {size}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap gap-1">
        <span className="mr-1 self-center text-muted">Overlay</span>
        {(["none", "crosshair", "grid", "plate_frame"] as const).map((overlay) => (
          <button
            key={overlay}
            type="button"
            onClick={() => onViewChange({ review_overlay: overlay })}
            className={`rounded border px-2 py-1 ${settings.review_overlay === overlay ? "border-accent-cyan bg-cyan-950/50 text-accent-cyan" : "border-border text-fg"}`}
          >
            {overlayLabel(overlay)}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-2 rounded border border-border bg-bg/60 px-2 py-1 text-fg">
        <span className="text-muted">Orientation</span>
        <span className="font-mono">{settings.rotate_deg}deg</span>
        {s1Preset && <span className="rounded bg-amber-950/40 px-1.5 py-0.5 text-accent-amber">S1 preset</span>}
      </div>
      <label className="grid gap-1">
        <span>Feed type</span>
        <select
          value={settings.feed_mode}
          disabled={!configured}
          onChange={(event) => {
            const feedMode = event.currentTarget.value === "snapshot" ? "snapshot" : "stream";
            onViewChange({ feed_mode: feedMode });
            if (feedMode === "snapshot") {
              onRefreshSnapshot();
            }
          }}
          className="rounded border border-border bg-bg px-2 py-1 text-fg disabled:opacity-50"
        >
          <option value="stream">Live stream</option>
          <option value="snapshot">Snapshot</option>
        </select>
      </label>
      <RangeControl icon={<ZoomIn size={12} />} label="Zoom" value={settings.zoom} min={0.5} max={4} step={0.1} suffix="x" onChange={(zoom) => onViewChange({ zoom })} />
      <RangeControl icon={<ZoomOut size={12} />} label="Focus X" value={settings.focus_x} min={0} max={100} step={1} suffix="%" onChange={(focus_x) => onViewChange({ focus_x })} />
      <RangeControl icon={<ZoomOut size={12} />} label="Focus Y" value={settings.focus_y} min={0} max={100} step={1} suffix="%" onChange={(focus_y) => onViewChange({ focus_y })} />
      <RangeControl label="Brightness" value={settings.brightness} min={40} max={180} step={1} suffix="%" onChange={(brightness) => onViewChange({ brightness })} />
      <RangeControl label="Contrast" value={settings.contrast} min={40} max={200} step={1} suffix="%" onChange={(contrast) => onViewChange({ contrast })} />
      <RangeControl label="Saturation" value={settings.saturation} min={0} max={220} step={1} suffix="%" onChange={(saturation) => onViewChange({ saturation })} />
    </div>
  );
}

function RangeControl({
  icon,
  label,
  value,
  min,
  max,
  step,
  suffix,
  onChange,
}: {
  icon?: ReactNode;
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  suffix: string;
  onChange: (value: number) => void;
}) {
  return (
    <label className="grid gap-1">
      <span className="flex items-center justify-between gap-2">
        <span className="inline-flex items-center gap-1">
          {icon}
          {label}
        </span>
        <span className="font-mono text-fg">{value}{suffix}</span>
      </span>
      <input
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(event) => onChange(Number(event.currentTarget.value))}
        className="w-full accent-cyan-400"
      />
    </label>
  );
}

function IconButton({ title, active = false, onClick, children }: { title: string; active?: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      className={`rounded border px-2 py-1 ${active ? "border-accent-cyan bg-cyan-950/60 text-accent-cyan" : "border-border text-fg"}`}
    >
      {children}
    </button>
  );
}

function FeedOverlay({ icon, title, detail }: { icon: ReactNode; title: string; detail: string }) {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-bg/80 p-4 text-center text-xs text-muted">
      <div className="text-accent-cyan">{icon}</div>
      <div className="font-semibold text-fg">{title}</div>
      <div className="max-w-xs">{detail}</div>
    </div>
  );
}

function ReviewOverlay({ mode }: { mode: CameraViewSettings["review_overlay"] }) {
  if (mode === "none") {
    return null;
  }
  if (mode === "crosshair") {
    return (
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-0 h-full w-px bg-accent-cyan/60" />
        <div className="absolute left-0 top-1/2 h-px w-full bg-accent-cyan/60" />
      </div>
    );
  }
  if (mode === "grid") {
    return (
      <div
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{
          backgroundImage: "linear-gradient(to right, rgba(34,211,238,.45) 1px, transparent 1px), linear-gradient(to bottom, rgba(34,211,238,.45) 1px, transparent 1px)",
          backgroundSize: "33.333% 33.333%",
        }}
      />
    );
  }
  return (
    <div className="pointer-events-none absolute inset-[8%] border border-accent-amber/70">
      <div className="absolute -left-px -top-px h-5 w-5 border-l-2 border-t-2 border-accent-amber" />
      <div className="absolute -right-px -top-px h-5 w-5 border-r-2 border-t-2 border-accent-amber" />
      <div className="absolute -bottom-px -left-px h-5 w-5 border-b-2 border-l-2 border-accent-amber" />
      <div className="absolute -bottom-px -right-px h-5 w-5 border-b-2 border-r-2 border-accent-amber" />
    </div>
  );
}

function isObserverAvailable(status: string): boolean {
  return status === "ACTIVE" || status === "configured" || status === "READY";
}

function initialFeedState(cameras: CameraFeed[]): Record<string, "loading" | "online" | "error"> {
  return Object.fromEntries(cameras.map((camera) => {
    if (!camera.camera_url) {
      return [camera.printer_id, "error"];
    }
    // Use real health from the backend probe — "unreachable" means the camera
    // is confirmed offline, so start in error state rather than "loading"
    // (which would make the UI appear to be trying to connect to a known-dead feed).
    if (camera.health === "unreachable") {
      return [camera.printer_id, "error"];
    }
    return [camera.printer_id, "loading"];
  }));
}

async function fetchCameras(): Promise<CameraFeed[]> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/observe/cameras`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => []);
    if (!response.ok) {
      throw new Error(cameraSummary(payload, response.statusText));
    }
    return Array.isArray(payload) ? payload.map(parseCamera).filter((camera): camera is CameraFeed => camera != null) : [];
  } catch (error) {
    throw new Error(`camera feed API is unreachable at ${LIVE_BASE_URL}: ${errorMessage(error)}`);
  }
}

/** Fetch GET /api/observe/status — per-camera online/offline + fps estimate.
 *  Read-only: no control commands are sent. S1 flag is backend-enforced.
 */
async function fetchObserveStatus(): Promise<ObserveStatusResponse> {
  const response = await fetch(`${LIVE_BASE_URL}/api/observe/status`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const payload: unknown = await response.json().catch(() => ({ cameras: [], online: 0, total: 0 }));
  if (!response.ok || !isRecord(payload)) {
    return { cameras: [], online: 0, total: 0 };
  }
  const rawCameras = Array.isArray(payload.cameras) ? payload.cameras : [];
  const cameras: CameraStatus[] = rawCameras
    .filter(isRecord)
    .map((c) => ({
      printer_id: String(c.printer_id ?? ""),
      printer_name: String(c.printer_name ?? ""),
      camera_url: typeof c.camera_url === "string" ? c.camera_url : null,
      health: parseHealthStatus(c.health),
      http_status: typeof c.http_status === "number" ? c.http_status : null,
      response_ms: typeof c.response_ms === "number" ? c.response_ms : null,
      estimated_fps: typeof c.estimated_fps === "number" ? c.estimated_fps : null,
      read_only: c.read_only === true,
    }));
  return {
    cameras,
    online: typeof payload.online === "number" ? payload.online : 0,
    total: typeof payload.total === "number" ? payload.total : 0,
  };
}

function parseHealthStatus(value: unknown): CameraStatus["health"] {
  if (
    value === "configured" ||
    value === "locked" ||
    value === "not_configured" ||
    value === "reachable" ||
    value === "unreachable" ||
    value === "unknown"
  ) {
    return value;
  }
  return "unknown";
}

async function markPlateClear(
  printerId: string,
  setCameras: Dispatch<SetStateAction<CameraFeed[]>>,
  setMessage: (message: string) => void,
) {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/observe/build-plate-clearance/${encodeURIComponent(printerId)}/clear`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({
        actor: "hermes-agent",
        reason: "Build plate visually confirmed clear from Observe camera/operator review.",
      }),
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    const plate = parsePlateClearance(payload);
    if (response.ok && plate) {
      setCameras((current) => current.map((camera) => camera.printer_id === plate.printer_id ? { ...camera, plate_clearance: plate } : camera));
      setMessage(`${plate.printer_name}: build plate marked clear by Hermes agent.`);
      await adapters.emitProofEvent("observe.build_plate.marked_clear", {
        printer_id: plate.printer_id,
        actor: "hermes-agent",
        last_job_filename: plate.last_job_filename,
      });
      return;
    }
    setMessage(`Blocked: ${cameraSummary(payload, response.statusText)}`);
  } catch {
    setMessage("Blocked: build plate clearance API is unreachable.");
  }
}

async function updateCameraView(
  printerId: string,
  updates: Partial<CameraViewSettings>,
  setCameras: Dispatch<SetStateAction<CameraFeed[]>>,
  setMessage: (message: string) => void,
) {
  let previousSettings: CameraViewSettings | null = null;
  setCameras((current) => current.map((camera) => (
    camera.printer_id === printerId
      ? (previousSettings = camera.view_settings, { ...camera, view_settings: sanitizeViewSettings({ ...camera.view_settings, ...updates }) })
      : camera
  )));
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/observe/cameras/${encodeURIComponent(printerId)}/view`, {
      method: "PUT",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(updates),
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    const settings = parseViewSettings(payload);
    if (response.ok && settings) {
      setCameras((current) => current.map((camera) => camera.printer_id === printerId ? { ...camera, view_settings: settings } : camera));
      return;
    }
    const previous = previousSettings;
    if (previous) {
      setCameras((current) => current.map((camera) => camera.printer_id === printerId ? { ...camera, view_settings: previous } : camera));
    }
    setMessage(`Blocked: ${cameraSummary(payload, response.statusText)}`);
  } catch {
    const previous = previousSettings;
    if (previous) {
      setCameras((current) => current.map((camera) => camera.printer_id === printerId ? { ...camera, view_settings: previous } : camera));
    }
    setMessage("Blocked: camera view settings API is unreachable.");
  }
}

async function probeCamera(printerId: string, setMessage: (message: string) => void) {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/observe/cameras/${encodeURIComponent(printerId)}/health`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    setMessage(`${response.ok ? "Health" : "Blocked"}: ${cameraSummary(payload, response.statusText)}`);
  } catch {
    setMessage("Blocked: observe backend API is unreachable.");
  }
}

function parseCamera(value: unknown): CameraFeed | null {
  if (!isRecord(value) || typeof value.printer_id !== "string" || typeof value.printer_name !== "string") {
    return null;
  }
  return {
    printer_id: value.printer_id,
    printer_name: value.printer_name,
    camera_url: typeof value.camera_url === "string" ? value.camera_url : null,
    health: parseHealth(value.health),
    is_locked: value.is_locked === true,
    printer_locked: value.printer_locked === true,
    camera_kind: parseCameraKind(value.camera_kind),
    camera_note: typeof value.camera_note === "string" ? value.camera_note : "Camera state unavailable.",
    stream_url: typeof value.stream_url === "string" ? value.stream_url : `/api/observe/cameras/${value.printer_id}/stream`,
    snapshot_url: typeof value.snapshot_url === "string" ? value.snapshot_url : `/api/observe/cameras/${value.printer_id}/snapshot`,
    view_settings: parseViewSettings(value.view_settings) ?? defaultViewSettings(value.printer_id),
    plate_clearance: parsePlateClearance(value.plate_clearance),
  };
}

function parsePlateClearance(value: unknown): BuildPlateClearance | null {
  if (!isRecord(value) || typeof value.printer_id !== "string" || typeof value.printer_name !== "string") {
    return null;
  }
  return {
    printer_id: value.printer_id,
    printer_name: value.printer_name,
    state: parsePlateState(value.state),
    last_job_filename: typeof value.last_job_filename === "string" ? value.last_job_filename : null,
    source: typeof value.source === "string" ? value.source : "unknown",
    reason: typeof value.reason === "string" ? value.reason : null,
    confirmed_by: typeof value.confirmed_by === "string" ? value.confirmed_by : null,
    confirmed_at: typeof value.confirmed_at === "string" ? value.confirmed_at : null,
    updated_at: typeof value.updated_at === "string" ? value.updated_at : null,
    camera_url: typeof value.camera_url === "string" ? value.camera_url : null,
    printer_locked: value.printer_locked === true,
  };
}

function parsePlateState(value: unknown): BuildPlateClearance["state"] {
  if (value === "clear" || value === "needs_clearance" || value === "locked" || value === "unknown") {
    return value;
  }
  return "unknown";
}

function parseViewSettings(value: unknown): CameraViewSettings | null {
  if (!isRecord(value)) {
    return null;
  }
  return sanitizeViewSettings({
    rotate_deg: parseRotation(value.rotate_deg),
    mirror_x: value.mirror_x === true,
    mirror_y: value.mirror_y === true,
    zoom: typeof value.zoom === "number" ? value.zoom : DEFAULT_VIEW_SETTINGS.zoom,
    focus_x: typeof value.focus_x === "number" ? value.focus_x : DEFAULT_VIEW_SETTINGS.focus_x,
    focus_y: typeof value.focus_y === "number" ? value.focus_y : DEFAULT_VIEW_SETTINGS.focus_y,
    brightness: typeof value.brightness === "number" ? value.brightness : DEFAULT_VIEW_SETTINGS.brightness,
    contrast: typeof value.contrast === "number" ? value.contrast : DEFAULT_VIEW_SETTINGS.contrast,
    saturation: typeof value.saturation === "number" ? value.saturation : DEFAULT_VIEW_SETTINGS.saturation,
    fit: value.fit === "contain" ? "contain" : "cover",
    feed_mode: value.feed_mode === "snapshot" ? "snapshot" : "stream",
    card_size: parseCardSize(value.card_size),
    review_overlay: parseOverlay(value.review_overlay),
  });
}

function defaultViewSettings(printerId: string): CameraViewSettings {
  return printerId === "flsun_s1" ? { ...DEFAULT_VIEW_SETTINGS, rotate_deg: 90, fit: "cover", card_size: "wide", zoom: 1.5, review_overlay: "plate_frame" } : { ...DEFAULT_VIEW_SETTINGS };
}

function parseRotation(value: unknown): CameraViewSettings["rotate_deg"] {
  if (value === 90 || value === 180 || value === 270) {
    return value;
  }
  return 0;
}

function parseOverlay(value: unknown): CameraViewSettings["review_overlay"] {
  if (value === "crosshair" || value === "grid" || value === "plate_frame") {
    return value;
  }
  return "none";
}

function parseCardSize(value: unknown): CameraViewSettings["card_size"] {
  if (value === "compact" || value === "wide" || value === "large" || value === "full") {
    return value;
  }
  return "standard";
}

function sanitizeViewSettings(value: CameraViewSettings): CameraViewSettings {
  const rotate: CameraViewSettings["rotate_deg"] = value.rotate_deg === 90 || value.rotate_deg === 180 || value.rotate_deg === 270 ? value.rotate_deg : 0;
  return {
    rotate_deg: rotate,
    mirror_x: value.mirror_x,
    mirror_y: value.mirror_y,
    zoom: clamp(value.zoom, 0.5, 4),
    focus_x: clamp(value.focus_x, 0, 100),
    focus_y: clamp(value.focus_y, 0, 100),
    brightness: clamp(value.brightness, 40, 180),
    contrast: clamp(value.contrast, 40, 200),
    saturation: clamp(value.saturation, 0, 220),
    fit: value.fit === "contain" ? "contain" : "cover",
    feed_mode: value.feed_mode === "snapshot" ? "snapshot" : "stream",
    card_size: parseCardSize(value.card_size),
    review_overlay: parseOverlay(value.review_overlay),
  };
}

function parseHealth(value: unknown): CameraHealth {
  if (value === "configured" || value === "locked" || value === "not_configured" || value === "reachable" || value === "unreachable" || value === "unknown") {
    return value;
  }
  return "unknown";
}

function parseCameraKind(value: unknown): CameraFeed["camera_kind"] {
  if (value === "integrated" || value === "usb_webcam" || value === "locked" || value === "external") {
    return value;
  }
  return "external";
}

function feedStateLabel(state: "loading" | "online" | "error" | "reconnecting", health: CameraHealth): string {
  if (state === "online") {
    return "LIVE";
  }
  if (state === "reconnecting") {
    return "RECONNECTING";
  }
  if (state === "error" || health === "unreachable") {
    return "UNREACHABLE";
  }
  return "CONNECTING";
}

function cameraKindLabel(kind: CameraFeed["camera_kind"]): string {
  if (kind === "integrated") {
    return "Integrated camera";
  }
  if (kind === "usb_webcam") {
    return "USB webcam";
  }
  if (kind === "locked") {
    return "Safety locked";
  }
  return "External camera";
}

function plateLabel(plate: BuildPlateClearance): string {
  if (plate.state === "needs_clearance") {
    return "plate needs clearance";
  }
  if (plate.state === "clear") {
    return "plate clear";
  }
  if (plate.state === "locked") {
    return "plate locked";
  }
  return "plate state unknown";
}

function statusClass(camera: CameraFeed, feedState: "loading" | "online" | "error" | "reconnecting"): string {
  const base = "shrink-0 rounded px-2 py-0.5 text-[10px] font-semibold";
  if (!camera.camera_url || feedState === "error") {
    return `${base} bg-surface2 text-muted`;
  }
  if (feedState === "online") {
    return `${base} bg-green-900/40 text-green-300`;
  }
  if (feedState === "reconnecting") {
    return `${base} bg-amber-900/40 text-amber-300`;
  }
  return `${base} bg-cyan-900/40 text-cyan-300`;
}

function cameraImageStyle(settings: CameraViewSettings): CSSProperties {
  return {
    objectFit: settings.fit,
    objectPosition: `${settings.focus_x}% ${settings.focus_y}%`,
    transform: `rotate(${settings.rotate_deg}deg) scaleX(${settings.mirror_x ? -1 : 1}) scaleY(${settings.mirror_y ? -1 : 1}) scale(${settings.zoom})`,
    transformOrigin: "center center",
    filter: `brightness(${settings.brightness}%) contrast(${settings.contrast}%) saturate(${settings.saturation}%)`,
  };
}

function cardSizeClassName(size: CameraViewSettings["card_size"]): string {
  if (size === "full") {
    return "lg:col-span-2 xl:col-span-2 2xl:col-span-4";
  }
  if (size === "large") {
    return "lg:col-span-2 xl:col-span-2 xl:row-span-2";
  }
  if (size === "wide") {
    return "lg:col-span-2 xl:col-span-2";
  }
  return "";
}

function cardMinHeightClass(size: CameraViewSettings["card_size"]): string {
  if (size === "compact") {
    return "min-h-[12rem]";
  }
  if (size === "large" || size === "full") {
    return "min-h-[20rem] xl:min-h-[22rem]";
  }
  return "min-h-[15rem]";
}

function overlayLabel(mode: CameraViewSettings["review_overlay"]): string {
  if (mode === "crosshair") {
    return "crosshair";
  }
  if (mode === "grid") {
    return "grid";
  }
  if (mode === "plate_frame") {
    return "plate frame";
  }
  return "overlay off";
}

function rotateLeft(current: CameraViewSettings["rotate_deg"]): CameraViewSettings["rotate_deg"] {
  return current === 0 ? 270 : current === 270 ? 180 : current === 180 ? 90 : 0;
}

function rotateRight(current: CameraViewSettings["rotate_deg"]): CameraViewSettings["rotate_deg"] {
  return current === 0 ? 90 : current === 90 ? 180 : current === 180 ? 270 : 0;
}

function rotateHalf(current: CameraViewSettings["rotate_deg"]): CameraViewSettings["rotate_deg"] {
  return current === 0 ? 180 : current === 90 ? 270 : current === 180 ? 0 : 90;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function viewModeLabel(mode: "all" | "selected" | "one" | "two" | "three"): string {
  if (mode === "one") {
    return "1";
  }
  if (mode === "two") {
    return "2";
  }
  if (mode === "three") {
    return "3";
  }
  if (mode === "selected") {
    return "selected";
  }
  return "all";
}

function cameraRowsForMode(
  cameras: CameraFeed[],
  visibleCameraIds: Record<string, boolean>,
  viewMode: "all" | "selected" | "one" | "two" | "three",
): CameraFeed[] {
  const selected = cameras.filter((camera) => visibleCameraIds[camera.printer_id] === true);
  if (viewMode === "selected") {
    return selected;
  }
  const base = selected.length > 0 ? selected : cameras;
  if (viewMode === "one") {
    return base.slice(0, 1);
  }
  if (viewMode === "two") {
    return base.slice(0, 2);
  }
  if (viewMode === "three") {
    return base.slice(0, 3);
  }
  return cameras;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, Number.isFinite(value) ? value : min));
}

function cameraSummary(value: unknown, fallback: string): string {
  if (!isRecord(value)) {
    return fallback || "No response body.";
  }
  return String(value.health ?? value.detail ?? fallback);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
