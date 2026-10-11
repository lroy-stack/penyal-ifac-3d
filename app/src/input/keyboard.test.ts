import { describe, expect, it } from "vitest";
import { attachKeyboard, type DialogWatcher } from "./keyboard";
import { InputHub } from "./state";

class FakeWindow {
  private readonly listeners = new Map<string, Set<(event: never) => void>>();
  addEventListener(type: string, listener: (event: never) => void): void {
    const set = this.listeners.get(type) ?? new Set();
    set.add(listener);
    this.listeners.set(type, set);
  }
  removeEventListener(type: string, listener: (event: never) => void): void {
    this.listeners.get(type)?.delete(listener);
  }
  key(type: "keydown" | "keyup", code: string): void {
    for (const listener of this.listeners.get(type) ?? []) {
      (listener as (event: unknown) => void)({
        code,
        repeat: false,
        ctrlKey: false,
        metaKey: false,
        altKey: false,
        target: null,
        preventDefault: () => undefined,
      });
    }
  }
}

function fakeDialogs(): DialogWatcher & { open: () => void; close: () => void } {
  let isOpen = false;
  const listeners = new Set<() => void>();
  return {
    isOpen: () => isOpen,
    onOpen: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    open: () => {
      isOpen = true;
      for (const listener of listeners) listener();
    },
    close: () => {
      isOpen = false;
    },
  };
}

function setup() {
  const hub = new InputHub();
  const win = new FakeWindow();
  const dialogs = fakeDialogs();
  const detach = attachKeyboard(hub, win as unknown as Window, dialogs);
  return { hub, win, dialogs, detach };
}

describe("attachKeyboard", () => {
  it("walks while a key is held", () => {
    const { hub, win } = setup();

    win.key("keydown", "KeyW");

    expect(hub.keyboardMove.y).toBe(1);
  });

  it("stops moving when a dialog opens while keys are held, and stays stopped after it closes", () => {
    const { hub, win, dialogs } = setup();
    win.key("keydown", "KeyW");
    win.key("keydown", "ShiftLeft");
    win.key("keydown", "ArrowLeft");
    expect(hub.keyboardMove.y).toBe(1);

    dialogs.open();
    expect(hub.keyboardMove).toEqual({ x: 0, y: 0 });
    expect(hub.keyboardTurn).toBe(0);
    expect(hub.run).toBe(false);

    win.key("keydown", "KeyW");
    dialogs.close();
    win.key("keyup", "KeyW");
    expect(hub.keyboardMove).toEqual({ x: 0, y: 0 });
  });

  it("ignores key presses while a dialog is open", () => {
    const { hub, win, dialogs } = setup();
    dialogs.open();

    win.key("keydown", "KeyW");

    expect(hub.keyboardMove).toEqual({ x: 0, y: 0 });
  });
});
