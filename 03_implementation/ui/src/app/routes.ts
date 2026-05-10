import {
  Activity,
  AppWindow,
  Archive,
  Bell,
  BookOpen,
  CheckSquare,
  Eye,
  FileText,
  Folder,
  Layers,
  LayoutDashboard,
  ListOrdered,
  Map,
  Mic,
  Pencil,
  Printer,
  Puzzle,
  ScrollText,
  Settings as SettingsIcon,
  ShieldCheck,
  Sparkles,
  Users,
  Workflow,
  Zap,
  type LucideIcon,
} from "lucide-react";

export type TabDef = { id: string; label: string; icon: LucideIcon };

/**
 * Top-level tab list. Order matters for the primary sidebar — keep
 * frequently-used tabs near the top, utility/maintenance tabs grouped at the
 * bottom (W15-A19 introduces the utility group).
 */
export const TABS: TabDef[] = [
  { id: "source_os", label: "Source OS", icon: Layers },
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "autopilot", label: "Autopilot", icon: Zap },
  { id: "design", label: "Design", icon: Pencil },
  { id: "gen3d", label: "3D Generation", icon: Sparkles },
  { id: "jobs", label: "Jobs", icon: ListOrdered },
  { id: "printers", label: "Printers", icon: Printer },
  { id: "observe", label: "Observe", icon: Eye },
  { id: "voice", label: "Voice", icon: Mic },
  { id: "agents", label: "Agents", icon: Users },
  { id: "learning", label: "Learning", icon: BookOpen },
  { id: "artifacts", label: "Artifacts", icon: Archive },
  { id: "approvals", label: "Approvals", icon: CheckSquare },
  { id: "apps", label: "Apps", icon: AppWindow },
  { id: "plugins", label: "Plugins", icon: Puzzle },
  // ---- W15-A19 utility tabs (sidebar group) ----
  { id: "workflows", label: "Workflows", icon: Workflow },
  { id: "print_queue", label: "Print Queue", icon: ListOrdered },
  { id: "files", label: "Files", icon: Folder },
  { id: "system_logs", label: "System Logs", icon: ScrollText },
  { id: "proof", label: "Proof", icon: FileText },
  { id: "service_health", label: "Service Health", icon: Activity },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "safety", label: "Safety", icon: ShieldCheck },
  // ---- meta ----
  { id: "settings", label: "Settings", icon: SettingsIcon },
  { id: "roadmap", label: "Roadmap", icon: Map },
];

/**
 * Tabs grouped as "utility / maintenance" — these are shown in their own
 * collapsible group at the bottom of the sidebar when the shell supports it.
 * Wave 15 A11 (sidebar shell) consumes this list directly.
 */
export const UTILITY_TAB_IDS: ReadonlyArray<string> = [
  "workflows",
  "print_queue",
  "files",
  "system_logs",
  "proof",
  "service_health",
  "notifications",
  "safety",
];

export const UTILITY_TABS: TabDef[] = TABS.filter((tab) => UTILITY_TAB_IDS.includes(tab.id));

export const PRIMARY_TABS: TabDef[] = TABS.filter(
  (tab) => tab.id !== "roadmap" && !UTILITY_TAB_IDS.includes(tab.id),
);
