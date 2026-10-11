import {
  CapsuleGeometry,
  Mesh,
  MeshStandardMaterial,
  type PerspectiveCamera,
  type Scene,
} from "three";
import { createInput } from "../input";
import { applyLookDelta, type Look } from "../input/mapping";
import type { Corridor, Enclosure, GroundSurface, HeightField } from "../world/ground";
import { AutoWalker, type AutoWalkRoute } from "./autowalk";
import { type CameraMode, CameraRig } from "./cameras";
import {
  CAPSULE_HEIGHT,
  CAPSULE_RADIUS,
  type ControllerOptions,
  MAX_FRAME_DT,
  PlayerController,
} from "./controller";

export type PlayerOptions = {
  readonly scene: Scene;
  readonly camera: PerspectiveCamera;
  readonly canvas: HTMLCanvasElement;
  readonly heightField: HeightField;
  readonly groundSurfaces: readonly GroundSurface[];
  /**
   * Hollow volumes (the tunnel): the height field inside them is rock the DEM fills in, not
   * ground, and the third-person camera stays inside them while the player is in them.
   */
  readonly enclosures?: readonly Enclosure[];
  readonly corridor: Corridor;
  readonly start: ControllerOptions["start"];
  /** Initial yaw (rad, 0 looks along -Z, positive turns left); defaults to 0. */
  readonly startYaw?: number;
};

/** Live, read-only view of the player; updated in place by `update`. */
export type PlayerState = {
  readonly position: { readonly x: number; readonly y: number; readonly z: number };
  readonly grounded: boolean;
  readonly cameraMode: CameraMode;
  readonly yaw: number;
  readonly pitch: number;
  /** The corridor limited the motion during the last update (show the "stay on the trail" note). */
  readonly corridorHit: boolean;
  /** The interact key was pressed during the last update. */
  readonly interactPressed: boolean;
  /** The auto-walk key was pressed during the last update. */
  readonly autowalkTogglePressed: boolean;
  /** Simulated seconds since creation. */
  readonly elapsed: number;
  readonly autowalk: {
    readonly active: boolean;
    /** Anchor the walk heads for; kept after arrival and null before the first walk. */
    readonly target: string | null;
    /** 0..1 along the route; 1 once the target is reached. */
    readonly progress: number;
  };
};

export type Player = {
  readonly update: (dt: number) => void;
  /** Starts walking the route by itself; manual movement or looking sideways cancels it. */
  readonly startAutoWalk: (route: AutoWalkRoute) => void;
  readonly stopAutoWalk: () => void;
  readonly dispose: () => void;
  readonly state: PlayerState;
};

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Wires input adapters, the kinematic controller and the camera rig. The capsule mesh stands in
 * for the character in third person until the real character arrives.
 */
export function createPlayer(options: PlayerOptions): Player {
  const input = createInput(options.canvas);
  const controller = new PlayerController({ ...options, hollows: options.enclosures ?? [] });
  const rig = new CameraRig(options.camera, {
    heightField: options.heightField,
    groundSurfaces: options.groundSurfaces,
    enclosures: options.enclosures ?? [],
    prefersReducedMotion,
  });

  const avatarGeometry = new CapsuleGeometry(
    CAPSULE_RADIUS,
    CAPSULE_HEIGHT - 2 * CAPSULE_RADIUS,
    4,
    12,
  );
  const avatarMaterial = new MeshStandardMaterial({ color: 0xd9822b, roughness: 0.8 });
  const avatar = new Mesh(avatarGeometry, avatarMaterial);
  avatar.visible = false;
  options.scene.add(avatar);

  let look: Look = { yaw: options.startYaw ?? 0, pitch: 0 };
  const live = {
    position: controller.state,
    grounded: true,
    cameraMode: rig.mode,
    yaw: 0,
    pitch: 0,
    corridorHit: false,
    interactPressed: false,
    autowalkTogglePressed: false,
    elapsed: 0,
    autowalk: { active: false, target: null as string | null, progress: 0 },
  };
  let walker: AutoWalker | null = null;

  const stopAutoWalk = (): void => {
    walker = null;
    live.autowalk.active = false;
  };

  const apply = (dt: number): void => {
    const feet = controller.state;
    avatar.position.set(feet.x, feet.y + CAPSULE_HEIGHT / 2, feet.z);
    avatar.rotation.y = look.yaw;
    avatar.visible = rig.mode === "third";
    live.grounded = feet.grounded;
    live.cameraMode = rig.mode;
    live.yaw = look.yaw;
    live.pitch = look.pitch;
    live.corridorHit = feet.corridorHit;
    live.elapsed += Math.min(Math.max(dt, 0), MAX_FRAME_DT);
  };

  rig.update(1 / 60, controller.state, look);
  apply(0);

  return {
    state: live,
    startAutoWalk: (route) => {
      walker = new AutoWalker(route);
      live.autowalk.active = true;
      live.autowalk.target = route.target;
      live.autowalk.progress = 0;
    },
    stopAutoWalk,
    update: (dt) => {
      const frame = input.hub.consume();
      look = applyLookDelta(look, { yaw: frame.lookYaw, pitch: frame.lookPitch });
      if (frame.toggleCamera) rig.toggle();
      live.interactPressed = frame.interact;
      live.autowalkTogglePressed = frame.toggleAutoWalk;
      const manual = frame.moveX !== 0 || frame.moveY !== 0 || frame.lookYaw !== 0;
      if (manual) stopAutoWalk();
      let move = { moveX: frame.moveX, moveY: frame.moveY, run: frame.run };
      if (walker !== null) {
        const command = walker.update(dt, controller.state, look.yaw);
        look = { yaw: command.yaw, pitch: look.pitch };
        move = command;
        live.autowalk.progress = walker.progress;
        if (command.done) stopAutoWalk();
      }
      controller.update(dt, { ...move, yaw: look.yaw });
      rig.update(dt, controller.state, look);
      apply(dt);
    },
    dispose: () => {
      input.dispose();
      options.scene.remove(avatar);
      avatarGeometry.dispose();
      avatarMaterial.dispose();
    },
  };
}
