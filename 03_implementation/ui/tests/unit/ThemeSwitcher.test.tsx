/**
 * W8-3 unit tests — ThemeSwitcher.
 *
 * Verifies dropdown open/close, mode selection wiring through the
 * provider, and ARIA attribute correctness.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { ThemeProvider } from "../../src/theme/ThemeProvider";
import { ThemeSwitcher } from "../../src/components/ThemeSwitcher/ThemeSwitcher";

beforeEach(() => {
  // Node 25's global localStorage lacks `clear()`; remove keys directly.
  window.localStorage.removeItem("h3d.theme");
  document.documentElement.className = "";
});

afterEach(() => {
  // testing-library auto-cleanup is wired only when `globals: true`. We
  // run with `globals: false` (matches W6-3 lane), so cleanup must be
  // explicit between tests.
  cleanup();
  window.localStorage.removeItem("h3d.theme");
});

function renderSwitcher(
  variant: "default" | "compact" = "default",
): ReturnType<typeof render> {
  return render(
    <ThemeProvider defaultTheme="dark">
      <ThemeSwitcher variant={variant} />
    </ThemeProvider>,
  );
}

describe("ThemeSwitcher", () => {
  it("renders a closed trigger and exposes ARIA expanded=false", () => {
    renderSwitcher();
    const trigger = screen.getByTestId("theme-switcher-trigger");
    expect(trigger).toBeInTheDocument();
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByTestId("theme-switcher-menu")).not.toBeInTheDocument();
  });

  it("opens the menu and lists three options", () => {
    renderSwitcher();
    fireEvent.click(screen.getByTestId("theme-switcher-trigger"));
    const menu = screen.getByTestId("theme-switcher-menu");
    expect(menu).toBeInTheDocument();
    expect(menu.getAttribute("role")).toBe("listbox");
    expect(screen.getByTestId("theme-switcher-option-light")).toBeInTheDocument();
    expect(screen.getByTestId("theme-switcher-option-dark")).toBeInTheDocument();
    expect(
      screen.getByTestId("theme-switcher-option-system"),
    ).toBeInTheDocument();
  });

  it("clicking 'Light' updates the theme + closes the menu", () => {
    renderSwitcher();
    fireEvent.click(screen.getByTestId("theme-switcher-trigger"));
    fireEvent.click(screen.getByTestId("theme-switcher-option-light"));
    expect(window.localStorage.getItem("h3d.theme")).toBe("light");
    expect(document.documentElement.classList.contains("light")).toBe(true);
    expect(screen.queryByTestId("theme-switcher-menu")).not.toBeInTheDocument();
  });

  it("aria-selected reflects the current theme", () => {
    renderSwitcher();
    fireEvent.click(screen.getByTestId("theme-switcher-trigger"));
    const dark = screen.getByTestId("theme-switcher-option-dark");
    expect(dark.getAttribute("aria-selected")).toBe("true");
    fireEvent.click(screen.getByTestId("theme-switcher-option-system"));
    fireEvent.click(screen.getByTestId("theme-switcher-trigger"));
    const sys = screen.getByTestId("theme-switcher-option-system");
    expect(sys.getAttribute("aria-selected")).toBe("true");
  });

  it("compact variant renders a single icon-only trigger", () => {
    renderSwitcher("compact");
    const trigger = screen.getByTestId("theme-switcher-trigger");
    // No visible label text in compact mode.
    expect(trigger.textContent?.trim() ?? "").toBe("");
  });

  it("Escape key closes the menu", () => {
    renderSwitcher();
    fireEvent.click(screen.getByTestId("theme-switcher-trigger"));
    expect(screen.getByTestId("theme-switcher-menu")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByTestId("theme-switcher-menu")).not.toBeInTheDocument();
  });
});
