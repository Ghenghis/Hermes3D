import { OperatorWorkbenchDashboard } from "./OperatorWorkbenchDashboard";

export function DashboardCreator() {
  return (
    <div
      className="dashboard-creator-shell relative flex h-full min-h-0 flex-col"
      data-testid="dashboard-creator-root"
      data-dashboard-mode="creator"
    >
      <OperatorWorkbenchDashboard
        modeId="creator"
        title="Create To Print"
        initialPreset="modeling"
        defaultActionTab="model"
      />
    </div>
  );
}
