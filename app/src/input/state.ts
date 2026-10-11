import { combineMoves, type MoveVector } from "./mapping";

/** What the player needs from input for one frame. Look deltas are radians since the last frame. */
export type InputState = {
  readonly moveX: number;
  readonly moveY: number;
  readonly lookYaw: number;
  readonly lookPitch: number;
  readonly run: boolean;
  /** True for exactly one frame per press. */
  readonly toggleCamera: boolean;
  /** True for exactly one frame per press. */
  readonly interact: boolean;
  /** True for exactly one frame per press. */
  readonly toggleAutoWalk: boolean;
};

export const IDLE_INPUT: InputState = {
  moveX: 0,
  moveY: 0,
  lookYaw: 0,
  lookPitch: 0,
  run: false,
  toggleCamera: false,
  interact: false,
  toggleAutoWalk: false,
};

/** Written by the adapters (keyboard, mouse, touch), read once per frame by the player. */
export class InputHub {
  keyboardMove: MoveVector = { x: 0, y: 0 };
  touchMove: MoveVector = { x: 0, y: 0 };
  run = false;
  private lookYaw = 0;
  private lookPitch = 0;
  private toggleCameraRequested = false;
  private interactRequested = false;
  private toggleAutoWalkRequested = false;

  addLook(yaw: number, pitch: number): void {
    this.lookYaw += yaw;
    this.lookPitch += pitch;
  }

  requestToggleCamera(): void {
    this.toggleCameraRequested = true;
  }

  requestInteract(): void {
    this.interactRequested = true;
  }

  requestToggleAutoWalk(): void {
    this.toggleAutoWalkRequested = true;
  }

  /** Returns this frame's input and clears the accumulated look deltas and one-shot presses. */
  consume(): InputState {
    const move = combineMoves(this.keyboardMove, this.touchMove);
    const state: InputState = {
      moveX: move.x,
      moveY: move.y,
      lookYaw: this.lookYaw,
      lookPitch: this.lookPitch,
      run: this.run,
      toggleCamera: this.toggleCameraRequested,
      interact: this.interactRequested,
      toggleAutoWalk: this.toggleAutoWalkRequested,
    };
    this.lookYaw = 0;
    this.lookPitch = 0;
    this.toggleCameraRequested = false;
    this.interactRequested = false;
    this.toggleAutoWalkRequested = false;
    return state;
  }

  /** Releases everything that is held (window blur, pointer lock lost). */
  reset(): void {
    this.keyboardMove = { x: 0, y: 0 };
    this.touchMove = { x: 0, y: 0 };
    this.run = false;
  }
}
