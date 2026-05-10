import {
  Archive,
  BookOpen,
  CheckSquare,
  Eye,
  Layers,
  LayoutDashboard,
  ListOrdered,
  Map,
  Mic,
  Pencil,
  Printer,
  Puzzle,
  Settings as SettingsIcon,
  Sparkles,
  Users,
  Zap,
  type LucideIcon,
} from "lucide-react";

export type TabDef = { id: string; label: string; icon: LucideIcon };

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
  { id: "plugins", label: "Plugins", icon: Puzzle },
  { id: "settings", label: "Settings", icon: SettingsIcon },
  { id: "roadmap", label: "Roadmap", icon: Map },
];

export const PRIMARY_TABS: TabDef[] = TABS.filter((tab) => tab.id !== "roadmap");
