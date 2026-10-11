import type { FrameSnapshot } from "../core/frameStats";

export type RenderLoad = { readonly calls: number; readonly triangles: number };

/** `?perf` switches the overlay on; `?perf=0` / `?perf=false` keep it off. */
export function isPerfRequested(search: string): boolean {
  const value = new URLSearchParams(search).get("perf");
  return value !== null && value !== "0" && value !== "false";
}

export function formatPerf(snapshot: FrameSnapshot | null, load: RenderLoad): string {
  if (snapshot === null) return "waiting for frames";
  const ms = (value: number): string => value.toFixed(1);
  return [
    `p50 ${ms(snapshot.p50)} | p95 ${ms(snapshot.p95)} | p99 ${ms(snapshot.p99)} ms`,
    `>50 ms: ${snapshot.over50} of ${snapshot.samples} (max ${Math.round(snapshot.max)} ms)`,
    `${load.calls} calls | ${Math.round(load.triangles / 1000)}k tris`,
  ].join("\n");
}

export type PerfOverlay = {
  readonly update: (snapshot: FrameSnapshot | null, load: RenderLoad) => void;
  readonly dispose: () => void;
};

/**
 * Small text box in the top-left corner with the raw frame-time statistics, also for reading
 * numbers off a real phone. It does not exist unless the page was opened with `?perf`, and it is
 * hidden from assistive technology and never takes pointer events.
 */
export function createPerfOverlay(host: HTMLElement = document.body): PerfOverlay {
  const element = document.createElement("pre");
  element.id = "perf";
  element.setAttribute("aria-hidden", "true");
  element.style.cssText =
    "position:fixed;top:max(0.5rem,env(safe-area-inset-top));left:max(0.5rem,env(safe-area-inset-left));" +
    "margin:0;padding:0.25rem 0.5rem;z-index:20;pointer-events:none;color:#9fffa8;" +
    "background:rgb(0 0 0 / 0.65);font:12px/1.35 ui-monospace,monospace;border-radius:4px;";
  host.append(element);
  return {
    update: (snapshot, load) => {
      element.textContent = formatPerf(snapshot, load);
    },
    dispose: () => element.remove(),
  };
}
