/**
 * 14 tabs: 13 from `hermes3d_gui_contract_kit_v4.1/01_requirements/TAB_SPECS.md`
 * plus Service Health (Task 4c — operator topology view, see
 * `handoffs/HANDOFF_TO_CODEX_HERMES3D_SERVICE_HEALTH.md`). Order + labels
 * for the kit-spec tabs MUST match; icons sourced from lucide-react.
 */
import {
  Activity,
  Box,
  GitBranch,
  LayoutDashboard,
  LayoutGrid,
  Layers,
  ListOrdered,
  Printer,
  ScrollText,
  Settings as SettingsIcon,
  ShieldCheck,
  Sliders,
  Sparkles,
  Users,
  type LucideIcon,
} from "lucide-react";

export type TabDef = { id: string; label: string; icon: LucideIcon };

export const TABS: TabDef[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "agents", label: "Agents", icon: Users },
  { id: "workflows", label: "Workflows", icon: GitBranch },
  { id: "gen3d", label: "3D Generation", icon: Sparkles },
  { id: "blender_mcp", label: "Blender MCP", icon: Box },
  { id: "slicing", label: "Slicing", icon: Layers },
  { id: "fleet", label: "Printer Fleet", icon: Printer },
  { id: "queue", label: "Print Queue", icon: ListOrdered },
  { id: "control", label: "Printer Control", icon: Sliders },
  { id: "docked", label: "Docked Apps", icon: LayoutGrid },
  { id: "proof", label: "Proof & Reports", icon: ShieldCheck },
  { id: "logs", label: "System Logs", icon: ScrollText },
  { id: "service_health", label: "Service Health", icon: Activity },
  { id: "settings", label: "Settings", icon: SettingsIcon },
];
