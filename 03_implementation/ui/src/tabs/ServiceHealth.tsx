/**
 * Service Health tab — promotes the existing `#health` gate page (W6-3 →
 * W8-1 → W14) into a first-class tab. The component itself already reads
 * `GET /api/health/services` and renders the full category/status grid.
 *
 * This wrapper just adds a tab-level `data-testid` so the visual oracle can
 * tell when the page is mounted vs. when the legacy #health shim is active.
 */

import { ServiceHealthPage } from "../components/health/ServiceHealthPage";

export function ServiceHealthTab() {
  return (
    <div data-testid="service-health-tab-root" className="h-full">
      <ServiceHealthPage />
    </div>
  );
}
