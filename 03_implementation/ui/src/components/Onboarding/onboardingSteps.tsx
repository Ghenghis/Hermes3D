/**
 * Step definitions for the W8-3 onboarding modal.
 *
 * Visuals are inline SVGs — no external image fetch, so the modal works
 * before the asset pipeline runs and Playwright can screenshot it
 * deterministically.  Each glyph is sized 360x180 (16:8 strip) to fit
 * the modal's 480px content area.
 */
import type { ReactNode } from "react";

export interface OnboardingStep {
  id: string;
  title: string;
  body: string;
  illustration: ReactNode;
}

function StripWrapper({ children }: { children: ReactNode }): JSX.Element {
  return (
    <div
      className="flex h-44 items-center justify-center rounded-md border border-border bg-surface"
      aria-hidden
    >
      {children}
    </div>
  );
}

const dashboardIllustration = (
  <StripWrapper>
    <svg
      viewBox="0 0 360 180"
      width="100%"
      height="100%"
      role="img"
      aria-label="Dashboard with three mode tiles"
    >
      <rect x="0" y="0" width="360" height="180" fill="transparent" />
      <rect x="14" y="20" width="332" height="22" rx="4" fill="#1f2a44" />
      <text x="22" y="35" fontSize="11" fill="#e6edf7" fontFamily="ui-sans-serif">
        AI-driven 3D Printing OS
      </text>
      <g>
        <rect x="14" y="56" width="100" height="106" rx="6" fill="#0f1626" stroke="#1f2a44" />
        <text x="24" y="74" fontSize="11" fill="#22d3ee" fontFamily="ui-sans-serif">Simple</text>
        <rect x="24" y="86" width="80" height="8" rx="2" fill="#1f2a44" />
        <rect x="24" y="100" width="60" height="8" rx="2" fill="#1f2a44" />
      </g>
      <g>
        <rect x="130" y="56" width="100" height="106" rx="6" fill="#0f1626" stroke="#22d3ee" />
        <text x="140" y="74" fontSize="11" fill="#22d3ee" fontFamily="ui-sans-serif">Advanced</text>
        <rect x="140" y="86" width="80" height="8" rx="2" fill="#1f2a44" />
        <rect x="140" y="100" width="60" height="8" rx="2" fill="#1f2a44" />
        <rect x="140" y="114" width="70" height="8" rx="2" fill="#1f2a44" />
      </g>
      <g>
        <rect x="246" y="56" width="100" height="106" rx="6" fill="#0f1626" stroke="#1f2a44" />
        <text x="256" y="74" fontSize="11" fill="#a78bfa" fontFamily="ui-sans-serif">Custom</text>
        <rect x="256" y="86" width="80" height="8" rx="2" fill="#1f2a44" />
        <rect x="256" y="100" width="60" height="8" rx="2" fill="#1f2a44" />
      </g>
    </svg>
  </StripWrapper>
);

const actionWindowIllustration = (
  <StripWrapper>
    <svg
      viewBox="0 0 360 180"
      width="100%"
      height="100%"
      role="img"
      aria-label="Action window with task list"
    >
      <rect x="14" y="14" width="332" height="152" rx="8" fill="#0f1626" stroke="#1f2a44" />
      <rect x="26" y="28" width="120" height="14" rx="3" fill="#22d3ee" opacity="0.3" />
      <text x="30" y="39" fontSize="10" fill="#22d3ee" fontFamily="ui-sans-serif">Action Window</text>
      <rect x="26" y="54" width="308" height="2" fill="#1f2a44" />
      {[0, 1, 2, 3].map((i) => (
        <g key={i} transform={`translate(0,${68 + i * 22})`}>
          <circle cx="36" cy="0" r="4" fill={i === 0 ? "#22c55e" : i === 1 ? "#f59e0b" : "#7c8aa8"} />
          <rect x="48" y="-6" width="220" height="12" rx="3" fill="#1f2a44" />
          <rect x="278" y="-6" width="50" height="12" rx="3" fill="#3b82f6" opacity="0.3" />
        </g>
      ))}
    </svg>
  </StripWrapper>
);

const taskMonitorIllustration = (
  <StripWrapper>
    <svg
      viewBox="0 0 360 180"
      width="100%"
      height="100%"
      role="img"
      aria-label="Task monitor with live queue"
    >
      <rect x="14" y="14" width="160" height="152" rx="6" fill="#0f1626" stroke="#1f2a44" />
      <text x="22" y="32" fontSize="10" fill="#a78bfa" fontFamily="ui-sans-serif">Pending</text>
      {[0, 1, 2, 3].map((i) => (
        <rect key={`p${i}`} x="22" y={42 + i * 16} width="140" height="10" rx="3" fill="#1f2a44" />
      ))}
      <rect x="184" y="14" width="160" height="152" rx="6" fill="#0f1626" stroke="#1f2a44" />
      <text x="192" y="32" fontSize="10" fill="#22c55e" fontFamily="ui-sans-serif">Running</text>
      <rect x="192" y="42" width="80" height="14" rx="3" fill="#22c55e" opacity="0.4" />
      <rect x="192" y="62" width="120" height="10" rx="3" fill="#1f2a44" />
      <rect x="192" y="78" width="100" height="10" rx="3" fill="#1f2a44" />
      <rect x="192" y="94" width="60" height="10" rx="3" fill="#1f2a44" />
    </svg>
  </StripWrapper>
);

const settingsIllustration = (
  <StripWrapper>
    <svg
      viewBox="0 0 360 180"
      width="100%"
      height="100%"
      role="img"
      aria-label="Settings with provider rows and theme picker"
    >
      <rect x="14" y="14" width="332" height="152" rx="8" fill="#0f1626" stroke="#1f2a44" />
      <text x="26" y="38" fontSize="11" fill="#e6edf7" fontFamily="ui-sans-serif">Settings · Providers</text>
      {[
        { label: "DeepSeek", state: "#22c55e" },
        { label: "MiniMax", state: "#22c55e" },
        { label: "SiliconFlow", state: "#f59e0b" },
        { label: "LM Studio", state: "#22c55e" },
      ].map((row, i) => (
        <g key={row.label} transform={`translate(0, ${56 + i * 22})`}>
          <rect x="26" y="0" width="160" height="14" rx="3" fill="#1f2a44" />
          <text x="32" y="11" fontSize="9" fill="#e6edf7" fontFamily="ui-mono">{row.label}</text>
          <circle cx="200" cy="7" r="4" fill={row.state} />
          <rect x="220" y="0" width="100" height="14" rx="3" fill="#1f2a44" />
          <text x="226" y="11" fontSize="9" fill="#7c8aa8" fontFamily="ui-mono">configure</text>
        </g>
      ))}
    </svg>
  </StripWrapper>
);

export const ONBOARDING_STEPS: ReadonlyArray<OnboardingStep> = [
  {
    id: "dashboard-modes",
    title: "Three dashboards, one OS",
    body: "Toggle between Simple, Advanced, and Custom layouts from the topbar. Your choice persists across reloads — no setting lives behind a menu.",
    illustration: dashboardIllustration,
  },
  {
    id: "action-window",
    title: "The Action Window is your remote control",
    body: "Every print, slice, and verify run flows through the Action Window. Inspect inputs, retry, or block-and-handoff a task without leaving the page.",
    illustration: actionWindowIllustration,
  },
  {
    id: "task-monitor",
    title: "Watch live tasks in the Task Monitor",
    body: "Pending, running, and recently-completed tasks stream side-by-side. Click any row to drill into the saga, evidence chain, and proof bundle.",
    illustration: taskMonitorIllustration,
  },
  {
    id: "settings",
    title: "Bring your own providers",
    body: "Hermes Agent runs on DeepSeek, MiniMax, SiliconFlow, and LM Studio out of the box. Pick a theme, plug in keys, and rotate priorities under Settings.",
    illustration: settingsIllustration,
  },
];
