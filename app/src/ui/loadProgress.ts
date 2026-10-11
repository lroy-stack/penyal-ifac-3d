export type LoadSteps = {
  /** Trail, tunnel and terrain manifest are in. */
  readonly data: boolean;
  /** Null when the terrain is not being streamed (missing or failed). */
  readonly terrain: {
    readonly farLoaded: boolean;
    readonly required: number;
    readonly loaded: number;
  } | null;
  /** The collision height field is in and the player exists. */
  readonly collision: boolean;
};

const WITH_TERRAIN = { data: 0.1, far: 0.3, coarse: 0.25, collision: 0.35 } as const;
const WITHOUT_TERRAIN = { data: 0.2, collision: 0.8 } as const;

/** Poster progress, 0..1, from what has arrived so far. */
export function loadProgress(steps: LoadSteps): number {
  const { terrain } = steps;
  if (terrain === null) {
    return (
      (steps.data ? WITHOUT_TERRAIN.data : 0) + (steps.collision ? WITHOUT_TERRAIN.collision : 0)
    );
  }
  const coarse = terrain.required > 0 ? Math.min(terrain.loaded / terrain.required, 1) : 0;
  const total =
    (steps.data ? WITH_TERRAIN.data : 0) +
    (terrain.farLoaded ? WITH_TERRAIN.far : 0) +
    coarse * WITH_TERRAIN.coarse +
    (steps.collision ? WITH_TERRAIN.collision : 0);
  return Math.min(total, 1);
}
