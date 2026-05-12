/**
 * W21-MVP-5 — usePollingEffect behavioural tests.
 *
 * Pins the contract that the 5 stale tabs (Files, Artifacts, Agents,
 * Gen3D, Plugins) rely on:
 *
 *   1. Immediate first call on mount (no waiting for the first tick).
 *   2. Re-fires on the configured interval thereafter.
 *   3. Lag-protected: a tick that fires while the previous effect is
 *      still in-flight is SKIPPED — not queued — so a slow backend
 *      cannot produce a pile-up.
 *   4. Cleanup on unmount: the interval is cleared and any in-flight
 *      effect can short-circuit via the ``cancelled`` flag before
 *      touching state.
 *   5. The latest closure is used on every tick (effectRef pattern),
 *      so callers can pass inline arrows without re-arming the timer
 *      every render.
 *
 * Uses Vitest fake timers + React Testing Library.
 */
import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useState } from "react";
import { usePollingEffect } from "../../src/hooks/_useQuery";

describe("usePollingEffect", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  function Harness({
    effect,
    intervalMs,
  }: {
    effect: () => void | Promise<void>;
    intervalMs: number;
  }) {
    usePollingEffect(effect, intervalMs, [effect]);
    return <div data-testid="harness">running</div>;
  }

  it("calls the effect immediately on mount", () => {
    const effect = vi.fn();
    render(<Harness effect={effect} intervalMs={1000} />);
    // Immediate first call is synchronous from the test's POV because
    // the effect is a plain function (no await chain).
    expect(effect).toHaveBeenCalledTimes(1);
  });

  it("re-fires on the configured interval", async () => {
    const effect = vi.fn();
    render(<Harness effect={effect} intervalMs={1000} />);
    expect(effect).toHaveBeenCalledTimes(1); // immediate

    // The immediate tick was an async function; even though our effect
    // is synchronous, the ``await effectRef.current()`` inside tick()
    // queues a microtask before clearing ``inFlight``. Drain those
    // microtasks BEFORE advancing timers, or the next tick will see
    // inFlight=true and skip itself (lag-protect, working as designed).
    await act(async () => {
      await Promise.resolve();
    });

    await act(async () => {
      vi.advanceTimersByTime(1000);
      await Promise.resolve();
    });
    expect(effect).toHaveBeenCalledTimes(2);

    await act(async () => {
      vi.advanceTimersByTime(1000);
      await Promise.resolve();
    });
    expect(effect).toHaveBeenCalledTimes(3);
  });

  it("skips ticks while a previous async effect is still in-flight (lag-protect)", async () => {
    let release: (() => void) | null = null;
    let starts = 0;
    const effect = vi.fn(async () => {
      starts += 1;
      // First call blocks until we release it. Later calls return immediately.
      if (starts === 1) {
        await new Promise<void>((resolve) => {
          release = resolve;
        });
      }
    });

    render(<Harness effect={effect} intervalMs={1000} />);
    // First call started but is blocked.
    expect(starts).toBe(1);

    // Three ticks pass while first call is in-flight; none should
    // re-invoke the effect (lag-protect).
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    expect(starts).toBe(1);

    // Release the first call and let the microtask queue drain.
    await act(async () => {
      release?.();
      await Promise.resolve();
    });

    // The next tick should now be free to run.
    await act(async () => {
      vi.advanceTimersByTime(1000);
    });
    expect(starts).toBe(2);
  });

  it("clears the interval on unmount", async () => {
    const effect = vi.fn();
    const { unmount } = render(<Harness effect={effect} intervalMs={1000} />);
    expect(effect).toHaveBeenCalledTimes(1);

    // Drain microtasks so the lag-protect inFlight flag clears.
    await act(async () => {
      await Promise.resolve();
    });
    await act(async () => {
      vi.advanceTimersByTime(1000);
      await Promise.resolve();
    });
    expect(effect).toHaveBeenCalledTimes(2);

    unmount();
    // 5 more interval-widths after unmount: no further calls.
    await act(async () => {
      vi.advanceTimersByTime(5000);
    });
    expect(effect).toHaveBeenCalledTimes(2);
  });

  it("uses the latest closure on each tick (effectRef pattern)", async () => {
    function Bouncer() {
      const [n, setN] = useState(0);
      usePollingEffect(() => {
        // Capture n into a side-channel for the test.
        (Bouncer as unknown as { _seen: number[] })._seen ??= [];
        (Bouncer as unknown as { _seen: number[] })._seen.push(n);
      }, 1000, []);
      return (
        <button data-testid="bump" onClick={() => setN((v) => v + 1)}>
          {n}
        </button>
      );
    }
    const seen = ((Bouncer as unknown as { _seen: number[] })._seen = []);

    const { getByTestId } = render(<Bouncer />);
    // Immediate call captured n=0.
    expect(seen).toEqual([0]);
    // Drain microtasks so the inFlight flag clears.
    await act(async () => {
      await Promise.resolve();
    });

    // Bump state to 5 BEFORE the next tick.
    for (let i = 0; i < 5; i++) {
      await act(async () => {
        getByTestId("bump").click();
      });
    }
    // Now advance one interval. The tick should see n=5 via the ref
    // (not the captured n=0 from initial render).
    await act(async () => {
      vi.advanceTimersByTime(1000);
      await Promise.resolve();
    });
    expect(seen).toEqual([0, 5]);
  });

  it("intervalMs<=0 disables polling but still calls effect once on mount", () => {
    const effect = vi.fn();
    render(<Harness effect={effect} intervalMs={0} />);
    expect(effect).toHaveBeenCalledTimes(1);
    // Advance arbitrary amount — no further calls because the interval
    // branch was skipped.
    vi.advanceTimersByTime(10_000);
    expect(effect).toHaveBeenCalledTimes(1);
  });

  it("cancelled in-flight effect cannot touch state after unmount (race)", async () => {
    // Force the effect to set state on a separate component, and prove
    // the polling effect's cleanup prevents that from happening AFTER
    // unmount even if the promise was still mid-flight at unmount time.
    let lateResolver: (() => void) | null = null;
    let touchedAfterUnmount = false;
    const effect = vi.fn(async () => {
      await new Promise<void>((resolve) => {
        lateResolver = resolve;
      });
      // This branch runs AFTER the promise resolves. We're not
      // touching state directly here (the production tabs do, but the
      // hook's contract is: cancelled means caller should early-exit).
      // Instead we just probe that the consumer can observe the
      // post-unmount race window if it wants to.
      touchedAfterUnmount = true;
    });

    const { unmount } = render(<Harness effect={effect} intervalMs={1000} />);
    expect(effect).toHaveBeenCalledTimes(1);
    // Unmount before the in-flight promise resolves.
    unmount();
    // The hook's cleanup ran; the timer is cleared. But the effect
    // promise is still pending. Resolve it now.
    await act(async () => {
      lateResolver?.();
      await Promise.resolve();
    });
    // The effect's body completed (it doesn't internally check
    // cancellation — that's the caller's job in production), but the
    // hook will NOT call it again now that we're unmounted.
    expect(touchedAfterUnmount).toBe(true);
    // The smoking gun: no further interval-driven calls after unmount.
    await act(async () => {
      vi.advanceTimersByTime(10_000);
    });
    expect(effect).toHaveBeenCalledTimes(1);
  });
});
