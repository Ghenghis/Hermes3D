/**
 * W8-3 unit tests — StatusBannerHost + buildBanners.
 *
 * Each canonical source is exercised independently, then the host's
 * dismiss behaviour is verified via an injected sourcesOverride.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { StatusBannerHost } from "../../src/components/StatusBanners/StatusBannerHost";
import { buildBanners } from "../../src/components/StatusBanners/useBannerSources";

const KEYS = ["h3d.banners.dismissed"];

beforeEach(() => {
  // Node 25's global localStorage lacks `clear()`; remove keys directly.
  KEYS.forEach((k) => window.localStorage.removeItem(k));
});

afterEach(() => {
  cleanup();
  KEYS.forEach((k) => window.localStorage.removeItem(k));
});

describe("buildBanners", () => {
  const noopNav = () => undefined;

  it("returns no banners for an empty source set", () => {
    expect(buildBanners({}, noopNav)).toEqual([]);
  });

  it("emits an outdated banner when versions mismatch", () => {
    const banners = buildBanners(
      {
        agent: {
          installed_version: "0.12.0",
          upstream_version: "0.13.0",
          upstream_release_url: "https://example/release",
        },
      },
      noopNav,
    );
    expect(banners).toHaveLength(1);
    expect(banners[0].id).toBe("agent-outdated");
    expect(banners[0].severity).toBe("warning");
  });

  it("emits an error banner for failed providers", () => {
    const banners = buildBanners(
      {
        providers: [
          { id: "lm", label: "LM Studio", state: "ok" },
          { id: "ds", label: "DeepSeek", state: "error" },
        ],
      },
      noopNav,
    );
    expect(banners).toHaveLength(1);
    expect(banners[0].id).toBe("provider-failure");
    expect(banners[0].severity).toBe("error");
    expect(banners[0].title).toContain("1 provider");
  });

  it("emits a recovery banner that is not user-dismissible", () => {
    const banners = buildBanners(
      {
        recovery: { active: true, phase: "saga step 2/5" },
      },
      noopNav,
    );
    expect(banners).toHaveLength(1);
    expect(banners[0].id).toBe("recovery-active");
    expect(banners[0].severity).toBe("info");
    expect(banners[0].dismissible).toBe(false);
  });

  it("emits a printer-safety error that is not dismissible", () => {
    const banners = buildBanners(
      {
        printerSafety: { blocked: true, reason: "bed temperature out of range" },
      },
      noopNav,
    );
    expect(banners[0].id).toBe("printer-safety");
    expect(banners[0].severity).toBe("error");
    expect(banners[0].dismissible).toBe(false);
  });

  it("emits multiple banners simultaneously", () => {
    const banners = buildBanners(
      {
        agent: {
          installed_version: "0.12.0",
          upstream_version: "0.13.0",
        },
        providers: [{ id: "ds", label: "DeepSeek", state: "error" }],
        recovery: { active: true },
        printerSafety: { blocked: true },
      },
      noopNav,
    );
    expect(banners.map((b) => b.id)).toEqual([
      "agent-outdated",
      "provider-failure",
      "recovery-active",
      "printer-safety",
    ]);
  });
});

describe("StatusBannerHost", () => {
  it("renders nothing when no banners are active", () => {
    const { container } = render(<StatusBannerHost sourcesOverride={{}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders a provider-failure banner with role=alert", () => {
    render(
      <StatusBannerHost
        sourcesOverride={{
          providers: [{ id: "ds", label: "DeepSeek", state: "error" }],
        }}
      />,
    );
    const banner = screen.getByTestId("status-banner-provider-failure");
    expect(banner).toBeInTheDocument();
    expect(banner.getAttribute("role")).toBe("alert");
    expect(banner.getAttribute("data-severity")).toBe("error");
  });

  it("dismiss button removes a dismissible banner from the host", () => {
    render(
      <StatusBannerHost
        sourcesOverride={{
          agent: {
            installed_version: "0.12.0",
            upstream_version: "0.13.0",
          },
        }}
      />,
    );
    expect(
      screen.getByTestId("status-banner-agent-outdated"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("status-banner-dismiss-agent-outdated"));
    expect(
      screen.queryByTestId("status-banner-agent-outdated"),
    ).not.toBeInTheDocument();
  });

  it("non-dismissible banner does not render an X button", () => {
    render(
      <StatusBannerHost
        sourcesOverride={{
          recovery: { active: true },
        }}
      />,
    );
    expect(screen.getByTestId("status-banner-recovery-active")).toBeInTheDocument();
    expect(
      screen.queryByTestId("status-banner-dismiss-recovery-active"),
    ).not.toBeInTheDocument();
  });

  it("status (info / success) banner uses role=status not role=alert", () => {
    render(
      <StatusBannerHost
        sourcesOverride={{ recovery: { active: true, phase: "running" } }}
      />,
    );
    const banner = screen.getByTestId("status-banner-recovery-active");
    expect(banner.getAttribute("role")).toBe("status");
  });
});
