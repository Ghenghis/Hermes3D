const NAV_ITEMS = [
  { key: "home", label: "Hermes3D OS", count: null },
  { key: "source_backed", label: "Source-backed Projects", count: null },
  { key: "slicers", label: "Slicers", count: null },
  { key: "modelers", label: "Modelers", count: null },
  { key: "print_farm", label: "Print Farm", count: null },
  { key: "firmware", label: "Firmware", count: null },
  { key: "three_d_generation", label: "3D Generation", count: null },
  { key: "agents", label: "Agents", count: null },
  { key: "library", label: "Library", count: null },
  { key: "materials", label: "Materials", count: null },
  { key: "hardware", label: "Hardware", count: null },
  { key: "utilities", label: "Utilities", count: null },
  { key: "research", label: "Research", count: null },
];

export function SecondaryNav({
  activeSection,
  counts,
  onSelect,
}: {
  activeSection: string;
  counts: Record<string, number>;
  onSelect: (section: string) => void;
}) {
  const total = Object.values(counts).reduce((sum, count) => sum + count, 0);
  return (
    <nav className="source-os-secondary-nav flex flex-wrap items-center gap-1 overflow-x-hidden border-b border-border bg-surface px-2 py-1">
      {NAV_ITEMS.map((item) => {
        const active = item.key === activeSection;
        const count = item.key === "source_backed" ? total : item.key === "home" ? null : counts[item.key] ?? 0;
        return (
          <button
            key={item.key}
            type="button"
            data-category={item.key}
            onClick={() => onSelect(item.key)}
            className={[
              "shrink-0 rounded px-2 py-1.5 text-[10.5px] font-medium transition-colors border-b-2",
              active
                ? "bg-surface2 text-fg border-accent-blue"
                : "text-muted hover:text-fg border-transparent",
            ].join(" ")}
          >
            <span>{item.label}</span>
            {count != null && (
              <span className="ml-1 rounded bg-bg/60 px-1.5 py-0.5 font-mono text-[10px]">
                {count}
              </span>
            )}
          </button>
        );
      })}
    </nav>
  );
}
