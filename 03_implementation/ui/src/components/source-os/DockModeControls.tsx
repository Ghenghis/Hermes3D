import { useEffect } from "react";

export type SourceOSDockMode = "dock" | "wide" | "full";

export function DockModeControls({
  mode,
  onChange,
}: {
  mode: SourceOSDockMode;
  onChange: (mode: SourceOSDockMode) => void;
}) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onChange("dock");
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onChange]);

  const selectMode = (nextMode: SourceOSDockMode) => {
    onChange(nextMode);
    if (nextMode === "full" && !document.fullscreenElement) {
      void document.documentElement.requestFullscreen().catch(() => undefined);
    }
  };

  return (
    <div className="inline-flex overflow-hidden rounded border border-border bg-surface2 text-[11px]">
      {(["dock", "wide", "full"] as const).map((nextMode) => (
        <button
          key={nextMode}
          type="button"
          onClick={() => selectMode(nextMode)}
          className={[
            "px-2.5 py-1 capitalize transition-colors",
            mode === nextMode ? "bg-accent-blue/20 text-accent-blue" : "text-muted hover:text-fg",
          ].join(" ")}
        >
          {nextMode}
        </button>
      ))}
    </div>
  );
}
