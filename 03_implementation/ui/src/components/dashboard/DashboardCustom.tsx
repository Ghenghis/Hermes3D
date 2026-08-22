import { OperatorWorkbenchDashboard } from "./OperatorWorkbenchDashboard";

export function DashboardCustom() {
  return (
    <div
      className="dashboard-custom-workbench relative flex h-full min-h-0 flex-col"
      data-testid="dashboard-custom-root"
      data-dashboard-mode="custom"
    >
      <OperatorWorkbenchDashboard
        modeId="custom"
        title="Custom Workbench"
        initialPreset="modeling"
        defaultActionTab="model"
      />
    </div>
  );
}
