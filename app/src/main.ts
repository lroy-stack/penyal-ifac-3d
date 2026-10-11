import { PerspectiveCamera, Scene, Vector2 } from "three";
import { type AppState, createAppState } from "./appState";
import { baseUrl, createAssetProvider } from "./core/assets";
import { createFrameClock } from "./core/frameClock";
import { type FrameSnapshot, FrameStats } from "./core/frameStats";
import { createPageLifecycle } from "./core/lifecycle";
import { createLoop } from "./core/loop";
import {
  probeDevice,
  profileFor,
  type QualityProfile,
  type QualityTier,
  resolveInitialProfile,
} from "./core/quality";
import { createRenderer } from "./core/renderer";
import { TEST_HOOKS_ENABLED } from "./core/testHooks";
import { parseTimescale, simulationSteps } from "./core/timescale";
import { createPlayer, type Player } from "./player";
import { buildAutoWalkRoute } from "./player/autowalk";
import { EYE_HEIGHT, MAX_FRAME_DT } from "./player/controller";
import { initCredits } from "./ui/credits";
import { createHud } from "./ui/hud";
import { loadProgress } from "./ui/loadProgress";
import { createPerfOverlay, isPerfRequested, type PerfOverlay } from "./ui/perfOverlay";
import { createPoster } from "./ui/poster";
import { t } from "./ui/strings";
import { createAtmosphere } from "./world/atmosphere";
import { dayAtmosphere } from "./world/atmosphere/defaults";
import { COLLISION_PATH, loadCollisionField } from "./world/collision";
import { type HeightField, PolygonCorridor } from "./world/ground";
import { createWorldSystems } from "./world/index";
import {
  createGroundRegistry,
  createWorld,
  EMPTY_POIS,
  type FrameInfo,
  type Route,
} from "./world/systems";
import type { TerrainStats } from "./world/terrain";
import type { TerrainGateOutcome } from "./world/terrain/gate";
import { GATE_CHECK_FRAMES } from "./world/terrain/system";
import {
  headingAlongRoute,
  loadTrail,
  markReachedAnchors,
  routePoints,
  startAnchor,
  TRAIL_PATH,
} from "./world/trail";
import { cameraFar, workAreaCentre } from "./world/workArea";

/** Anchors count as reached within this horizontal distance (m). */
const ANCHOR_REACH_RADIUS = 6;
/** The terrain statistics are refreshed every N frames; they allocate. */
const STATS_INTERVAL_FRAMES = 15;
/** How long "the terrain is available now" stays up after a late recovery. */
const RECOVERED_NOTICE_MS = 5000;
/** Auto-walk target of the P key. */
const DEFAULT_AUTOWALK_TARGET = "summit";

function requireElement<T extends HTMLElement>(id: string, type: new () => T): T {
  const element = document.getElementById(id);
  if (!(element instanceof type)) {
    throw new Error(`index.html is missing the #${id} element.`);
  }
  return element;
}

function setStatus(message: string): void {
  requireElement("status", HTMLDivElement).textContent = message;
}

function showFatal(message: string): void {
  const fatal = requireElement("fatal", HTMLDivElement);
  fatal.textContent = message;
  fatal.dataset.visible = "true";
  createPoster().hide();
  setStatus(message);
}

let failed = false;
let stopRendering: () => void = () => undefined;

/**
 * Every fatal path ends here: the loop stops (so nothing renders behind the message and a
 * `pageshow` cannot revive it), no notice stays on top, and the fatal screen is shown.
 */
function fail(message: string): void {
  failed = true;
  stopRendering();
  showFatal(message);
}

function describeError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function debugFlags(params: URLSearchParams): ReadonlySet<string> {
  const value = params.get("debug");
  return new Set(value === null ? [] : value.split(","));
}

/**
 * The bootstrap: device probe, quality profile, renderer, camera and scene; the atmosphere and
 * the list of world systems; the route; the loop and the walk gate; the collision field and the
 * player. What is drawn, and how it loads, is in the systems (`world/index.ts`).
 */
async function bootstrap(): Promise<void> {
  const canvas = requireElement("scene", HTMLCanvasElement);
  const poster = createPoster();
  const hud = createHud();
  stopRendering = () => hud.notify(null);
  const camera = new PerspectiveCamera(65, 1, 0.2, cameraFar());

  const device = probeDevice();
  const quality: { current: QualityProfile } = {
    current: resolveInitialProfile(device, location.search),
  };
  const handle = createRenderer(
    canvas,
    (width, height) => {
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    },
    { coarsePointer: device.coarsePointer, quality },
  );
  if (!handle.ok) {
    fail(handle.message);
    return;
  }
  const { renderer } = handle;

  setStatus(t("loadingRoute"));
  const params = new URLSearchParams(location.search);
  const scene = new Scene();
  const assets = createAssetProvider(renderer, baseUrl());
  const ground = createGroundRegistry();

  const state: AppState = createAppState();
  state.quality = quality.current;
  if (TEST_HOOKS_ENABLED) {
    state.timescale = parseTimescale(location.search);
    window.__appState = state;
  }
  const clock = createFrameClock(() => state.timescale);

  let resolveRoute: (route: Route) => void = () => undefined;
  const route = new Promise<Route>((resolve) => {
    resolveRoute = resolve;
  });
  let resolveCollision: (field: HeightField) => void = () => undefined;
  // Never settles when the collision field fails: the fatal screen has replaced the scene by then.
  const collisionField = new Promise<HeightField>((resolve) => {
    resolveCollision = resolve;
  });

  const atmosphere = createAtmosphere(dayAtmosphere(workAreaCentre()));
  const { systems, handles } = createWorldSystems({
    atmosphere,
    debugTrail: debugFlags(params).has("trail"),
  });
  handles.tunnel.onMesh = (result) => {
    if (result.ok) {
      state.tunnel.meshLoaded = true;
    } else {
      state.tunnel.message = result.message;
      setStatus(t("tunnelMissing"));
    }
  };
  const world = createWorld(systems, {
    scene,
    camera,
    renderer,
    assets,
    atmosphere,
    quality,
    ground,
    pois: EMPTY_POIS,
    route,
    collision: collisionField,
    params,
    testHooks: TEST_HOOKS_ENABLED,
  });

  // Small files first: they say what to fetch next. trail.json and the critical systems (the
  // terrain manifest, tunnel.json) are requested together; the collision field (about 1 MB) is
  // not: it competes for bandwidth with the terrain, which is what the visitor sees.
  const trailLoad = loadTrail(assets.url(TRAIL_PATH));
  const critical = world.init("critical");
  const beforeWalk = world.init("beforeWalk");
  let trail: Awaited<typeof trailLoad>;
  try {
    trail = await trailLoad;
  } catch (error) {
    world.dispose();
    assets.dispose();
    handle.dispose();
    fail(`${t("routeDataFailed")} ${describeError(error)}`);
    return;
  }
  const corridor = new PolygonCorridor(trail.corridor.polygon.map(([x, z]) => [x, z] as const));
  const start = startAnchor(trail, params.get("start"), corridor).anchor;
  const startYaw = headingAlongRoute(routePoints(trail), start);
  resolveRoute({ trail, corridor, start, startYaw });
  await Promise.all([critical, beforeWalk]);

  const systemStatus = world.status();
  const terrainStatus = systemStatus.terrain;
  if (terrainStatus?.state === "ready") {
    state.terrain.status = "ready";
    setStatus(t("loadingTerrain"));
    poster.setMessage(t("loadingTerrain"));
  } else if (terrainStatus?.state === "missing") {
    state.terrain.status = "missing";
    setStatus(t("terrainMissing"));
  } else {
    const message = handles.terrain.error() ?? terrainStatus?.state ?? "unknown";
    state.terrain.status = "error";
    state.terrain.message = message;
    setStatus(`${t("terrainFailed")} ${message}`);
  }
  const tunnelStatus = systemStatus.tunnel;
  if (tunnelStatus?.state === "ready" || tunnelStatus?.state === "degraded") {
    state.tunnel.status = "ready";
  } else if (tunnelStatus?.state === "missing") {
    state.tunnel.status = "missing";
  } else {
    const message = handles.tunnel.error() ?? tunnelStatus?.state ?? "unknown";
    state.tunnel.status = "error";
    state.tunnel.message = message;
    setStatus(`${t("tunnelFailed")} ${message}`);
  }

  const frameStats = new FrameStats();
  const perfOverlay: PerfOverlay | null = isPerfRequested(location.search)
    ? createPerfOverlay()
    : null;
  let lastSnapshot: FrameSnapshot | null = null;
  const drawingBuffer = new Vector2();

  let player: Player | null = null;
  let collisionLoaded = false;
  const terrainView: { outcome: TerrainGateOutcome } = { outcome: "waiting" };
  let openWalkGate: () => void = () => undefined;
  const walkGate = new Promise<void>((resolve) => {
    openWalkGate = resolve;
  });
  const pollWalkGate = (): void => {
    if (world.isSettled()) openWalkGate();
  };
  pollWalkGate();

  const progressNow = (stats: TerrainStats | null): number =>
    loadProgress({
      data: true,
      terrain:
        stats === null
          ? null
          : {
              farLoaded: stats.farLoaded,
              required: stats.coverage.required,
              loaded: stats.coverage.loaded,
            },
      collision: collisionLoaded,
    });

  // Before the collision field arrives there is no player: the camera rests at the start and the
  // loop only streams and draws the terrain, so it can be shown as soon as it is there.
  const startEye = { x: start.x, y: start.y + EYE_HEIGHT, z: start.z };
  camera.position.set(startEye.x, startEye.y, startEye.z);
  camera.rotation.set(0, startYaw, 0, "YXZ");

  const showTerrainOutcome = (outcome: TerrainGateOutcome, stats: TerrainStats): void => {
    const before = terrainView.outcome;
    // Once the walk has started, the streamer also loads detail tiles, so its progress no longer
    // means the failed critical path is coming back: after a failure only visibility counts.
    if (before === "failed" && player !== null && outcome !== "visible") return;
    terrainView.outcome = outcome;
    if (outcome === "visible") {
      state.loading.terrainVisibleMs = Math.round(performance.now());
      poster.hide();
      if (before === "failed") {
        state.terrain.status = "ready";
        state.terrain.message = null;
        setStatus(t("terrainRecovered"));
        hud.notify(t("terrainRecovered"), RECOVERED_NOTICE_MS);
      } else {
        // One polite live region announces it: #notice (the visible message), not #status as well.
        hud.notify(t("terrainReady"));
      }
    } else if (outcome === "failed") {
      if (before !== "failed") {
        state.terrain.status = "error";
        state.terrain.message = stats.lastError ?? "The terrain did not load in time.";
        setStatus(`${t("terrainFailed")} ${stats.lastError ?? ""}`.trim());
        poster.setMessage(t("terrainFailed"));
        // Said once when it happens; a failure before the walk is announced when the walk starts.
        if (player !== null) hud.notify(t("terrainFailed"));
      }
    } else if (before === "failed") {
      state.terrain.status = "ready";
      state.terrain.message = null;
      setStatus(t("loadingTerrain"));
      poster.setMessage(t("loadingTerrain"));
      if (player !== null) hud.notify(t("loadingTerrain"));
    }
  };

  /**
   * Until the terrain is visible (also after a failure: a slow link may still deliver it), the
   * terrain system feeds its progress to the stall gate every few frames, on the real frame time
   * (capped per frame, zero while the tab is hidden), not on the simulation dt, which is clamped
   * and would stretch the deadline at low frame rates. Each step is shown here.
   */
  const showGateStep = (): void => {
    const step = handles.terrain.takeGateStep();
    if (step === null) return;
    state.terrain.stats = step.stats;
    poster.setProgress(progressNow(step.stats));
    showTerrainOutcome(step.outcome, step.stats);
  };

  const syncSystems = (): void => {
    const status = world.status();
    const cpu = world.cpuMs();
    for (const [id, systemState] of Object.entries(status)) {
      state.systems[id] = { status: systemState, cpuMs: cpu[id] ?? 0 };
    }
  };

  if (TEST_HOOKS_ENABLED) {
    window.__world = {
      setEnabled: (id, enabled) => {
        world.setEnabled(id, enabled);
        syncSystems();
      },
      freezeTime: (seconds) => clock.freeze(seconds),
      setQuality: (tier: QualityTier) => {
        const next: QualityProfile = { ...profileFor(tier, device), source: "override" };
        world.setQuality(next);
        state.quality = next;
      },
    };
  }

  const previewFrame = (info: FrameInfo): void => {
    world.update("prePlayer", info);
    world.update("postPlayer", info);
    world.update("preRender", info);
    renderer.render(scene, camera);
  };

  const reached = new Set<string>();
  let startAutoWalk: (target: string) => void = () => undefined;

  const liveFrame = (current: Player, dt: number, info: FrameInfo): void => {
    world.update("prePlayer", info);
    for (const step of simulationSteps(dt, state.timescale, MAX_FRAME_DT)) {
      current.update(step);
      if (current.state.autowalkTogglePressed) {
        if (current.state.autowalk.active) current.stopAutoWalk();
        else startAutoWalk(DEFAULT_AUTOWALK_TARGET);
      }
    }
    world.update("postPlayer", info);
    world.update("preRender", info);
    renderer.render(scene, camera);

    state.frames++;
    const { position, grounded, cameraMode, yaw, corridorHit, elapsed } = current.state;
    Object.assign(state.player, {
      x: position.x,
      y: position.y,
      z: position.z,
      yaw,
      grounded,
      cameraMode,
      corridorHit,
      elapsed,
    });
    if (markReachedAnchors(position, trail.anchors, ANCHOR_REACH_RADIUS, reached).length > 0) {
      state.anchorsReached = [...reached];
    }
    Object.assign(state.autowalk, current.state.autowalk);
    state.camera.x = camera.position.x;
    state.camera.y = camera.position.y;
    state.camera.z = camera.position.z;
    state.render.calls = renderer.info.render.calls;
    state.render.triangles = renderer.info.render.triangles;
    state.render.programs = renderer.info.programs?.length ?? 0;
    hud.update(corridorHit, performance.now(), t("corridorNotice"));

    if (state.frames % STATS_INTERVAL_FRAMES === 1) {
      const stats = handles.terrain.stats();
      if (stats !== null) state.terrain.stats = stats;
    }
    if (TEST_HOOKS_ENABLED) syncSystems();
    state.ready = true;
  };

  const loop = createLoop((dt, rawMs) => {
    if (rawMs !== null) frameStats.push(rawMs);
    const tick = clock.next(dt, rawMs);
    renderer.getDrawingBufferSize(drawingBuffer);
    const info: FrameInfo = {
      ...tick,
      drawingBufferHeight: drawingBuffer.y,
      player: player?.state ?? null,
    };
    if (player === null) previewFrame(info);
    else liveFrame(player, dt, info);
    showGateStep();
    if (tick.frame % GATE_CHECK_FRAMES === 1) pollWalkGate();
    if (frameStats.snapshot !== lastSnapshot) {
      lastSnapshot = frameStats.snapshot;
      state.frameStats = lastSnapshot;
      state.frameTimeP95Ms = lastSnapshot?.p95 ?? null;
      perfOverlay?.update(lastSnapshot, state.render);
    }
  });
  if (handles.terrain.available()) loop.start();

  stopRendering = () => {
    loop.stop();
    hud.notify(null);
  };

  const lifecycle = createPageLifecycle({
    suspend: () => loop.stop(),
    resume: () => {
      if (!failed) loop.start();
    },
    dispose: () => {
      player?.dispose();
      world.dispose();
      perfOverlay?.dispose();
      hud.dispose();
      assets.dispose();
      handle.dispose();
    },
  });
  window.addEventListener("pagehide", lifecycle.onPageHide);
  window.addEventListener("pageshow", lifecycle.onPageShow);

  // The walk starts only once every critical system has settled (the terrain is visible, or it
  // has given up, or it is missing); then the collision field is fetched.
  await walkGate;
  let collision: Awaited<ReturnType<typeof loadCollisionField>>;
  try {
    collision = await loadCollisionField(assets.url(COLLISION_PATH));
  } catch (error) {
    fail(`${t("routeDataFailed")} ${describeError(error)}`);
    return;
  }
  collisionLoaded = true;
  resolveCollision(collision);
  poster.setProgress(progressNow(state.terrain.stats));

  const startFloor = ground.startFloor(start.x, start.z);
  const created = createPlayer({
    scene,
    camera,
    canvas,
    heightField: collision,
    groundSurfaces: ground.surfaces,
    enclosures: ground.enclosures,
    corridor,
    start:
      startFloor === null ? { x: start.x, z: start.z } : { x: start.x, z: start.z, y: startFloor },
    startYaw,
  });

  startAutoWalk = (target: string): void => {
    try {
      created.startAutoWalk(buildAutoWalkRoute(trail.route.segments, trail.anchors, target));
    } catch (error) {
      setStatus(`${t("autowalkFailed")} ${describeError(error)}`);
    }
  };
  player = created;
  world.startWalk();
  state.loading.readyMs = Math.round(performance.now());
  poster.hide();
  if (terrainView.outcome === "failed") hud.notify(t("terrainFailed"));
  else hud.notify(null);
  setStatus(
    terrainView.outcome === "failed" ? `${t("walkReady")} ${t("terrainFailed")}` : t("walkReady"),
  );
  hud.showHints(device.coarsePointer ? t("hintTouch") : t("hintKeyboard"));
  const requestedAutoWalk = params.get("autowalk");
  if (requestedAutoWalk !== null && requestedAutoWalk !== "") startAutoWalk(requestedAutoWalk);
  loop.start();
}

initCredits();
bootstrap().catch((error: unknown) => {
  fail(`${t("startFailed")} ${describeError(error)}`);
});
