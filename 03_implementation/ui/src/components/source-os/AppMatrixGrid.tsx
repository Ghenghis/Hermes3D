/**
 * AppMatrixGrid — pure layout wrapper for the 60-App Coverage Matrix.
 *
 * Picks a responsive grid (auto-fill, 180px min) that lands roughly on
 * 10 columns at the 1672x941 reference viewport — matches the
 * `source-os-60-app-coverage-matrix.png` collage from Images-GUI.
 *
 * Sources consulted:
 *   - React Grid Layout responsive cols pattern
 *     <https://github.com/react-grid-layout/react-grid-layout> — chose
 *     CSS Grid `auto-fill` over the JS-based layout engine because the
 *     matrix is static (no drag).
 *   - VS Code Marketplace listing grid layout
 *     <https://marketplace.visualstudio.com/vscode> — 4-to-10 column
 *     responsive tile pattern for 60+ extensions.
 *
 * Owner: claude-w15-a13-source-os.
 */

import type { ReactNode } from "react";

export interface AppMatrixGridProps {
  /** Card elements (typically <AppCard /> instances). */
  children: ReactNode;
  /**
   * Optional override for the minimum card width. The actual column
   * count is computed by CSS Grid from `minmax(<min>, 1fr)` against the
   * available container width.
   */
  minCardWidth?: string;
  /** Optional test id passthrough. */
  testId?: string;
}

export function AppMatrixGrid({
  children,
  minCardWidth = "168px",
  testId = "app-matrix-grid",
}: AppMatrixGridProps) {
  return (
    <div
      data-testid={testId}
      className="grid w-full gap-2"
      style={{ gridTemplateColumns: `repeat(auto-fill, minmax(${minCardWidth}, 1fr))` }}
      role="list"
      aria-label="60-app coverage matrix"
    >
      {children}
    </div>
  );
}
