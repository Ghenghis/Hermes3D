/**
 * Vitest suite for the Action Window.
 *
 * Covers:
 *   - Pure resize math (computeNextSize / capToViewport / clamp).
 *   - localStorage persistence round-trip.
 *   - Render of the panel, tabs, resize handles, and pop-out button.
 *
 * Run with: npx vitest run src/components/ActionWindow
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import {
  capToViewport,
  clamp,
  computeNextSize,
  loadPersistedSize,
  persistSize,
  ACTION_WINDOW_STORAGE_KEY,
} from "./useResizable";
import { ActionWindow } from "./ActionWindow";

afterEach(() => {
  cleanup();
  if (typeof window !== "undefined") {
    window.localStorage.clear();
  }
});

describe("computeNextSize", () => {
  const limits = { minWidth: 600, minHeight: 400, maxWidth: 1920, maxHeight: 1080 };

  it("grows width on right-handle drag", () => {
    const next = computeNextSize({ width: 800, height: 500 }, 100, 0, "right", limits);
    expect(next).toEqual({ width: 900, height: 500 });
  });

  it("grows height on bottom-handle drag", () => {
    const next = computeNextSize({ width: 800, height: 500 }, 0, 80, "bottom", limits);
    expect(next).toEqual({ width: 800, height: 580 });
  });

  it("grows both on corner-handle drag", () => {
    const next = computeNextSize({ width: 800, height: 500 }, 50, 30, "corner", limits);
    expect(next).toEqual({ width: 850, height: 530 });
  });

  it("clamps to minimums", () => {
    const next = computeNextSize({ width: 700, height: 450 }, -500, -500, "corner", limits);
    expect(next).toEqual({ width: 600, height: 400 });
  });

  it("clamps to maxes (viewport)", () => {
    const next = computeNextSize({ width: 1900, height: 1070 }, 500, 500, "corner", limits);
    expect(next).toEqual({ width: 1920, height: 1080 });
  });
});

describe("capToViewport", () => {
  it("shrinks oversized state to viewport", () => {
    const cropped = capToViewport(
      { width: 4000, height: 3000 },
      { minWidth: 600, minHeight: 400, maxWidth: 1920, maxHeight: 1080 },
    );
    expect(cropped).toEqual({ width: 1920, height: 1080 });
  });

  it("expands undersized state to minimums", () => {
    const grown = capToViewport(
      { width: 100, height: 50 },
      { minWidth: 600, minHeight: 400, maxWidth: 1920, maxHeight: 1080 },
    );
    expect(grown).toEqual({ width: 600, height: 400 });
  });
});

describe("clamp", () => {
  it("returns min for NaN", () => {
    expect(clamp(Number.NaN, 100, 1000)).toBe(100);
  });
  it("respects bounds", () => {
    expect(clamp(50, 100, 1000)).toBe(100);
    expect(clamp(2000, 100, 1000)).toBe(1000);
    expect(clamp(500, 100, 1000)).toBe(500);
  });
});

describe("localStorage persistence", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("round-trips a stored size", () => {
    persistSize(ACTION_WINDOW_STORAGE_KEY, { width: 1200, height: 720 });
    const loaded = loadPersistedSize(ACTION_WINDOW_STORAGE_KEY, { width: 0, height: 0 });
    expect(loaded).toEqual({ width: 1200, height: 720 });
  });

  it("falls back when storage is empty", () => {
    const loaded = loadPersistedSize(ACTION_WINDOW_STORAGE_KEY, { width: 800, height: 500 });
    expect(loaded).toEqual({ width: 800, height: 500 });
  });

  it("falls back when storage has corrupt JSON", () => {
    window.localStorage.setItem(ACTION_WINDOW_STORAGE_KEY, "{not json");
    const loaded = loadPersistedSize(ACTION_WINDOW_STORAGE_KEY, { width: 800, height: 500 });
    expect(loaded).toEqual({ width: 800, height: 500 });
  });

  it("disables persistence when key is null", () => {
    persistSize(null, { width: 1, height: 1 });
    const loaded = loadPersistedSize(null, { width: 800, height: 500 });
    expect(loaded).toEqual({ width: 800, height: 500 });
    expect(window.localStorage.length).toBe(0);
  });
});

describe("<ActionWindow />", () => {
  it("renders root with embedded data attribute", () => {
    render(<ActionWindow initialSize={{ width: 800, height: 500 }} />);
    const root = screen.getByTestId("action-window-root");
    expect(root).toBeInTheDocument();
    expect(root).toHaveAttribute("data-detached", "false");
  });

  it("renders all three resize handles when embedded", () => {
    render(<ActionWindow initialSize={{ width: 800, height: 500 }} />);
    expect(screen.getByTestId("action-window-handle-right")).toBeInTheDocument();
    expect(screen.getByTestId("action-window-handle-bottom")).toBeInTheDocument();
    expect(screen.getByTestId("action-window-handle-corner")).toBeInTheDocument();
  });

  it("hides resize handles when detached", () => {
    render(<ActionWindow detached />);
    expect(screen.queryByTestId("action-window-handle-right")).not.toBeInTheDocument();
    expect(screen.queryByTestId("action-window-handle-bottom")).not.toBeInTheDocument();
  });

  it("exposes the pop-out button", () => {
    render(<ActionWindow initialSize={{ width: 800, height: 500 }} />);
    const popout = screen.getByTestId("action-window-popout");
    expect(popout).toBeInTheDocument();
    expect(popout).toHaveAttribute("aria-label", "Open Action Window in new tab");
  });

  it("renders three tabs and switches the active panel on click", () => {
    render(<ActionWindow initialSize={{ width: 800, height: 500 }} />);
    expect(screen.getByTestId("action-window-tab-code")).toBeInTheDocument();
    expect(screen.getByTestId("action-window-tab-output")).toBeInTheDocument();
    expect(screen.getByTestId("action-window-tab-diff")).toBeInTheDocument();
    expect(screen.getByTestId("action-window-panel-code")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("action-window-tab-output"));
    expect(screen.getByTestId("action-window-panel-output")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("action-window-tab-diff"));
    expect(screen.getByTestId("action-window-panel-diff")).toBeInTheDocument();
  });

  it("calls window.open when pop-out is clicked", () => {
    const openSpy = vi.spyOn(window, "open").mockReturnValue(null);
    render(<ActionWindow initialSize={{ width: 800, height: 500 }} />);
    fireEvent.click(screen.getByTestId("action-window-popout"));
    expect(openSpy).toHaveBeenCalledWith(
      "/action-window?detached=1",
      "hermes3d-action-window",
      "noopener,noreferrer",
    );
    openSpy.mockRestore();
  });

  it("renders the size label when embedded", () => {
    render(<ActionWindow initialSize={{ width: 720, height: 480 }} />);
    expect(screen.getByTestId("action-window-size-label")).toHaveTextContent("720×480");
  });
});
