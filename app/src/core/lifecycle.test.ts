import { describe, expect, it, vi } from "vitest";
import { createPageLifecycle } from "./lifecycle";

function setup() {
  const actions = { suspend: vi.fn(), resume: vi.fn(), dispose: vi.fn() };
  return { actions, handlers: createPageLifecycle(actions) };
}

describe("createPageLifecycle", () => {
  it("only suspends when the page enters the bfcache", () => {
    const { actions, handlers } = setup();

    handlers.onPageHide({ persisted: true });

    expect(actions.suspend).toHaveBeenCalledOnce();
    expect(actions.dispose).not.toHaveBeenCalled();
  });

  it("suspends and disposes when the page is really unloaded", () => {
    const { actions, handlers } = setup();

    handlers.onPageHide({ persisted: false });

    expect(actions.suspend).toHaveBeenCalledOnce();
    expect(actions.dispose).toHaveBeenCalledOnce();
  });

  it("resumes on a bfcache restore", () => {
    const { actions, handlers } = setup();

    handlers.onPageShow({ persisted: true });

    expect(actions.resume).toHaveBeenCalledOnce();
  });

  it("ignores the pageshow of the initial load", () => {
    const { actions, handlers } = setup();

    handlers.onPageShow({ persisted: false });

    expect(actions.resume).not.toHaveBeenCalled();
  });
});
