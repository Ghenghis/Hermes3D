import { OperatorWorkbenchDashboard } from "./OperatorWorkbenchDashboard";

export function DashboardFactory() {
  return (
    <div
      className="dashboard-factory-shell relative flex h-full min-h-0 flex-col"
      data-testid="dashboard-factory-root"
      data-dashboard-mode="factory"
    >
      <OperatorWorkbenchDashboard
        modeId="factory"
        title="Live Factory"
        initialPreset="monitoring"
        defaultActionTab="console"
      />
    </div>
  );
}
