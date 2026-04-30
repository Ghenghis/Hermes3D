# React/Tailwind UI Structure

## Stack
- React + Vite
- Tailwind
- lucide-react icons
- recharts for charts
- Playwright for screenshot gate

## Suggested folders
```text
src/
  app/
    AppShell.tsx
    routes.tsx
  components/
    cards/
    layout/
    tables/
    badges/
    dock/
    proof/
  tabs/
    Dashboard.tsx
    Agents.tsx
    Workflows.tsx
    Generation3D.tsx
    BlenderMCP.tsx
    Slicing.tsx
    PrinterFleet.tsx
    PrintQueue.tsx
    PrinterControl.tsx
    DockedApps.tsx
    ProofReports.tsx
    SystemLogs.tsx
    Settings.tsx
  data/mock/
  api/
  styles/
```

## Design system tokens
- Background: near-black blue/graphite.
- Cards: layered dark surfaces.
- Borders: subtle cyan/blue glow.
- Accents: cyan, green, amber, red.
- Radius: 16–24px.
- Spacing: 4/8/12/16/24/32.
- Icons: 18–22px.
- Tables: dense rows with status chips.

## Hard rule
No tab-specific custom style system. All tabs reuse shared primitives.
