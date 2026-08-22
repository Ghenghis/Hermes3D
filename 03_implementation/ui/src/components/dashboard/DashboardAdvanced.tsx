import { OperatorWorkbenchDashboard } from "./OperatorWorkbenchDashboard";

export function DashboardAdvanced() {
  return (
    <div
      className="dashboard-advanced-shell relative flex h-full min-h-0 flex-col"
      data-testid="dashboard-advanced-root"
      data-dashboard-mode="advanced"
    >
      <OperatorWorkbenchDashboard />
    </div>
  );
}
