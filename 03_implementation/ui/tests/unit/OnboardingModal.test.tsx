/**
 * W8-3 unit tests — OnboardingModal.
 *
 * Verifies step navigation, dismissal persistence, and ARIA dialog
 * attributes.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  OnboardingModal,
  resetOnboarding,
  shouldShowOnboarding,
} from "../../src/components/Onboarding/OnboardingModal";
import { ONBOARDING_STEPS } from "../../src/components/Onboarding/onboardingSteps";

const STORAGE_KEY = "h3d.onboarding.dismissed";

beforeEach(() => {
  // Node 25's global localStorage lacks `clear()`; remove keys directly.
  window.localStorage.removeItem(STORAGE_KEY);
});

afterEach(() => {
  cleanup();
  window.localStorage.removeItem(STORAGE_KEY);
});

function renderModal(onClose = vi.fn()) {
  const utils = render(<OnboardingModal open onClose={onClose} />);
  return { onClose, ...utils };
}

describe("OnboardingModal", () => {
  it("returns null when open=false", () => {
    const { container } = render(
      <OnboardingModal open={false} onClose={() => undefined} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the first step and ARIA dialog attributes", () => {
    renderModal();
    const dialog = screen.getByTestId("onboarding-modal");
    expect(dialog.getAttribute("role")).toBe("dialog");
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    expect(screen.getByText(ONBOARDING_STEPS[0].title)).toBeInTheDocument();
  });

  it("Next button advances through every step then closes with reason=completed", () => {
    const { onClose } = renderModal();
    for (let i = 0; i < ONBOARDING_STEPS.length - 1; i += 1) {
      expect(screen.getByText(ONBOARDING_STEPS[i].title)).toBeInTheDocument();
      fireEvent.click(screen.getByTestId("onboarding-next"));
    }
    expect(screen.getByText(ONBOARDING_STEPS.at(-1)!.title)).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("onboarding-next"));
    expect(onClose).toHaveBeenCalledWith("completed");
    expect(window.localStorage.getItem(STORAGE_KEY)).not.toBeNull();
  });

  it("Skip button calls onClose with reason=skipped", () => {
    const { onClose } = renderModal();
    fireEvent.click(screen.getByTestId("onboarding-close"));
    expect(onClose).toHaveBeenCalledWith("skipped");
  });

  it("Back button is disabled on the first step and enabled afterwards", () => {
    renderModal();
    expect(screen.getByTestId("onboarding-back")).toBeDisabled();
    fireEvent.click(screen.getByTestId("onboarding-next"));
    expect(screen.getByTestId("onboarding-back")).not.toBeDisabled();
    fireEvent.click(screen.getByTestId("onboarding-back"));
    expect(screen.getByText(ONBOARDING_STEPS[0].title)).toBeInTheDocument();
  });

  it("does not persist when 'don't show again' is unchecked", () => {
    const { onClose } = renderModal();
    fireEvent.click(screen.getByTestId("onboarding-dont-show-again"));
    fireEvent.click(screen.getByTestId("onboarding-close"));
    expect(onClose).toHaveBeenCalledWith("skipped");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("ArrowRight + ArrowLeft keys navigate steps", () => {
    renderModal();
    expect(screen.getByText(ONBOARDING_STEPS[0].title)).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(screen.getByText(ONBOARDING_STEPS[1].title)).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(screen.getByText(ONBOARDING_STEPS[0].title)).toBeInTheDocument();
  });

  it("Escape closes with reason=dismissed", () => {
    const { onClose } = renderModal();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledWith("dismissed");
  });
});

describe("shouldShowOnboarding / resetOnboarding", () => {
  it("returns true when no record exists", () => {
    expect(shouldShowOnboarding()).toBe(true);
  });

  it("returns false after dismissal", () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ dismissedAtMs: 1 }));
    expect(shouldShowOnboarding()).toBe(false);
  });

  it("resetOnboarding wipes the record", () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ dismissedAtMs: 1 }));
    resetOnboarding();
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});
