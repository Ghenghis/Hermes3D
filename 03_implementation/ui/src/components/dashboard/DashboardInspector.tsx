import { OperatorWorkbenchDashboard } from "./OperatorWorkbenchDashboard";

export function DashboardInspector() {
  return (
    <div
      className="dashboard-inspector-shell relative flex h-full min-h-0 flex-col"
      data-testid="dashboard-inspector-root"
      data-dashboard-mode="inspector"
    >
      <OperatorWorkbenchDashboard
        modeId="inspector"
        title="Live Inspector"
        initialPreset="software"
        defaultActionTab="printer"
      />
    </div>
  );
}
