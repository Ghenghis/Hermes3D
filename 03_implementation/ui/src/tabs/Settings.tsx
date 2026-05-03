/**
 * Settings tab — host shell that delegates to the four canonical subtabs:
 * Providers, Printers, Environment, About.
 *
 * The full implementation lives in `components/settings/SettingsPage.tsx`
 * so the subtab tree is testable in isolation. AppShell renders this tab
 * when `activeTabId === "settings"` (wired via `App.tsx`).
 */
import { SettingsPage } from "../components/settings/SettingsPage";

export function SettingsTab() {
  return <SettingsPage />;
}
