import { Color, PerspectiveCamera, Scene, Vector2 } from "three";
import { type AppState, createAppState } from "./appState";
import { baseUrl, createGltfLoader, type GltfLoaderHandle, publicUrl } from "./core/assets";
import { type FrameSnapshot, FrameStats } from "./core/frameStats";
import { createPageLifecycle } from "./core/lifecycle";
import { createLoop } from "./core/loop";
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
import { COLLISION_PATH, loadCollisionField } from "./world/collision";
import { createTrailDebug, type TrailDebug } from "./world/debugTrail";
import { PolygonCorridor } from "./world/ground";
import { createSea } from "./world/sea";
import { createFog, createSky, HORIZON_COLOR } from "./world/sky";
import {
  createGltfTileLoader,
  createTerrainStreamer,
  loadTerrainManifest,
  sseThreshold,
  type TerrainStats,
  type TerrainStreamer,
  viewFromCamera,
} from "./world/terrain";
import {
  INITIAL_TERRAIN_GATE,
  stepTerrainGate,
  type TerrainGateOutcome,
} from "./world/terrain/gate";
import {
  headingAlongRoute,
  loadTrail,
  markReachedAnchors,
  routePoints,
  startAnchor,
  TRAIL_PATH,
} from "./world/trail";
import {
  loadTunnel,
  TUNNEL_DIRECTORY,
  TUNNEL_PATH,
  type Tunnel,
  TunnelGroundSurface,
} from "./world/tunnel";
import { createTunnelLamp, loadTunnelView, type TunnelView } from "./world/tunnelView";
import { cameraFar } from "./world/workArea";

/** Anchors count as reached within this horizontal distance (m). */
const ANCHOR_REACH_RADIUS = 6;
/** The terrain statistics are refreshed every N frames; they allocate. */
const STATS_INTERVAL_FRAMES = 15;
/** While the terrain loads, its readiness is checked every N frames. */
const PREVIEW_CHECK_FRAMES = 6;
/** How long "the terrain is available now" stays up after a late recovery. */
const RECOVERED_NOTICE_MS = 5000;
/** Longest frame the terrain gate counts, so one long stall (a debugger pause) does not end it. */
const GATE_MAX_FRAME_MS = 1000;
const TERRAIN_MANIFEST_PATH = "assets/generated/terrain/manifest.json";
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

function debugFlags(): ReadonlySet<string> {
  const value = new URLSearchParams(location.search).get("debug");
  return new Set(value === null ? [] : value.split(","));
}

async function bootstrap(): Promise<void> {
  const canvas = requireElement("scene", HTMLCanvasElement);
  const poster = createPoster();
  const hud = createHud();
  stopRendering = () => hud.notify(null);
  const far = cameraFar();
  const camera = new PerspectiveCamera(65, 1, 0.2, far);

  const handle = createRenderer(canvas, (width, height) => {
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  });
  if (!handle.ok) {
    fail(handle.message);
    return;
  }
  const { renderer } = handle;

  setStatus(t("loadingRoute"));
  const coarsePointer = window.matchMedia("(pointer: coarse)").matches;
  const base = baseUrl();
  const manifestUrl = publicUrl(TERRAIN_MANIFEST_PATH, base);

  // Small files first: they say what to fetch next. The collision field (about 1 MB) is not
  // requested here: it competes for bandwidth with the terrain, which is what the visitor sees.
  let trail: Awaited<ReturnType<typeof loadTrail>>;
  let manifest: Awaited<ReturnType<typeof loadTerrainManifest>>;
  let tunnelFile: Awaited<ReturnType<typeof loadTunnel>>;
  try {
    [trail, manifest, tunnelFile] = await Promise.all([
      loadTrail(publicUrl(TRAIL_PATH, base)),
      loadTerrainManifest(manifestUrl),
      loadTunnel(publicUrl(TUNNEL_PATH, base)),
    ]);
  } catch (error) {
    handle.dispose();
    fail(`${t("routeDataFailed")} ${describeError(error)}`);
    return;
  }

  const params = new URLSearchParams(location.search);
  const corridor = new PolygonCorridor(trail.corridor.polygon.map(([x, z]) => [x, z] as const));
  const start = startAnchor(trail, params.get("start"), corridor).anchor;
  const startYaw = headingAlongRoute(routePoints(trail), start);
  const summit = trail.anchors.summit ?? start;

  const scene = new Scene();
  scene.background = new Color(HORIZON_COLOR);
  scene.fog = createFog(summit);
  const sky = createSky(far * 0.9);
  scene.add(sky.object);
  scene.add(createSea());

  const state: AppState = createAppState();
  if (TEST_HOOKS_ENABLED) {
    state.timescale = parseTimescale(location.search);
    window.__appState = state;
  }

  let tunnel: Tunnel | null = null;
  let tunnelSurface: TunnelGroundSurface | null = null;
  if (tunnelFile.status === "ready") {
    tunnel = tunnelFile.tunnel;
    tunnelSurface = new TunnelGroundSurface(tunnel);
    state.tunnel.status = "ready";
  } else if (tunnelFile.status === "missing") {
    state.tunnel.status = "missing";
  } else {
    state.tunnel.status = "error";
    state.tunnel.message = tunnelFile.message;
  }

  let assets: GltfLoaderHandle | null = null;
  let streamer: TerrainStreamer | null = null;
  if (manifest.status === "ready") {
    assets = createGltfLoader(renderer);
    streamer = createTerrainStreamer({
      manifest: manifest.manifest,
      manifestUrl,
      load: createGltfTileLoader(assets.loader),
      sseThreshold: sseThreshold(coarsePointer),
      detailEnabled: false,
    });
    scene.add(streamer.root);
    state.terrain.status = "ready";
    setStatus(t("loadingTerrain"));
    poster.setMessage(t("loadingTerrain"));
  } else if (manifest.status === "missing") {
    state.terrain.status = "missing";
    setStatus(t("terrainMissing"));
  } else {
    state.terrain.status = "error";
    state.terrain.message = manifest.message;
    setStatus(`${t("terrainFailed")} ${manifest.message}`);
  }

  let trailDebug: TrailDebug | null = null;

  let tunnelView: TunnelView | null = null;
  const tunnelLamp = createTunnelLamp();
  if (tunnel !== null) {
    scene.add(tunnelLamp.light);
    assets ??= createGltfLoader(renderer);
    const tunnelUrl = publicUrl(`${TUNNEL_DIRECTORY}${tunnel.mesh}`, base);
    loadTunnelView(assets.loader, tunnelUrl).then(
      (view) => {
        tunnelView = view;
        scene.add(view.object);
        state.tunnel.meshLoaded = true;
      },
      (error: unknown) => {
        state.tunnel.message = `The tunnel interior could not be loaded. ${describeError(error)}`;
        setStatus(t("tunnelMissing"));
      },
    );
  } else if (tunnelFile.status === "error") {
    setStatus(`${t("tunnelFailed")} ${tunnelFile.message}`);
  }

  const frameStats = new FrameStats();
  const perfOverlay: PerfOverlay | null = isPerfRequested(location.search)
    ? createPerfOverlay()
    : null;
  let lastSnapshot: FrameSnapshot | null = null;
  const drawingBuffer = new Vector2();

  let player: Player | null = null;
  let collisionLoaded = false;
  let gateFrames = 0;
  let gateElapsedMs = 0;
  let gate = INITIAL_TERRAIN_GATE;
  const terrainView: { outcome: TerrainGateOutcome } = { outcome: "waiting" };
  let terrainSettled: () => void = () => undefined;
  const terrainGate = new Promise<void>((resolve) => {
    terrainSettled = resolve;
  });
  if (streamer === null) terrainSettled();

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
      terrainSettled();
    } else if (outcome === "failed") {
      if (before !== "failed") {
        state.terrain.status = "error";
        state.terrain.message = stats.lastError ?? "The terrain did not load in time.";
        setStatus(`${t("terrainFailed")} ${stats.lastError ?? ""}`.trim());
        poster.setMessage(t("terrainFailed"));
        terrainSettled();
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
   * Until the terrain is visible (also after a failure: a slow link may still deliver it), every
   * few frames the streamer's progress is fed to the stall gate with the real frame time, which is
   * zero while the tab is hidden.
   */
  const checkTerrainGate = (dt: number): void => {
    if (streamer === null || state.loading.terrainVisibleMs !== null) return;
    gateElapsedMs += dt * 1000;
    gateFrames++;
    if (gateFrames % PREVIEW_CHECK_FRAMES !== 1) return;
    const stats = streamer.stats();
    state.terrain.stats = stats;
    poster.setProgress(progressNow(stats));
    const step = stepTerrainGate(
      gate,
      {
        visible: stats.visible,
        gaveUp: stats.gaveUp,
        bytesLoaded: stats.bytesLoaded,
        loadedTiles: stats.coverage.loaded,
      },
      gateElapsedMs,
    );
    gate = step.state;
    gateElapsedMs = 0;
    showTerrainOutcome(step.outcome, stats);
  };

  const previewFrame = (): void => {
    sky.update(camera.position);
    if (streamer === null) return;
    renderer.getDrawingBufferSize(drawingBuffer);
    streamer.update(viewFromCamera(camera, drawingBuffer.y));
    renderer.render(scene, camera);
  };

  const reached = new Set<string>();
  let startAutoWalk: (target: string) => void = () => undefined;

  const liveFrame = (current: Player, dt: number): void => {
    for (const step of simulationSteps(dt, state.timescale, MAX_FRAME_DT)) {
      current.update(step);
      if (current.state.autowalkTogglePressed) {
        if (current.state.autowalk.active) current.stopAutoWalk();
        else startAutoWalk(DEFAULT_AUTOWALK_TARGET);
      }
    }
    const feet = current.state.position;
    tunnelLamp.update(
      { x: feet.x, y: feet.y, z: feet.z },
      tunnelSurface?.contains(feet.x, feet.y + 0.8, feet.z, 0) ?? false,
    );
    sky.update(camera.position);
    if (streamer !== null) {
      renderer.getDrawingBufferSize(drawingBuffer);
      streamer.update(viewFromCamera(camera, drawingBuffer.y));
    }
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
    hud.update(corridorHit, performance.now(), t("corridorNotice"));

    if (streamer !== null && state.frames % STATS_INTERVAL_FRAMES === 1) {
      state.terrain.stats = streamer.stats();
    }
    state.ready = true;
  };

  const loop = createLoop((dt, rawMs) => {
    if (rawMs !== null) frameStats.push(rawMs);
    if (player === null) previewFrame();
    else liveFrame(player, dt);
    // The gate runs on real elapsed time (capped per frame, zero while hidden), not on the
    // simulation dt, which is clamped to 0.1 s and would stretch the deadline at low frame rates.
    checkTerrainGate(rawMs === null ? 0 : Math.min(rawMs, GATE_MAX_FRAME_MS) / 1000);
    if (frameStats.snapshot !== lastSnapshot) {
      lastSnapshot = frameStats.snapshot;
      state.frameStats = lastSnapshot;
      state.frameTimeP95Ms = lastSnapshot?.p95 ?? null;
      perfOverlay?.update(lastSnapshot, state.render);
    }
  });
  if (streamer !== null) loop.start();

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
      streamer?.dispose();
      trailDebug?.dispose();
      perfOverlay?.dispose();
      hud.dispose();
      tunnelView?.dispose();
      tunnelLamp.light.dispose();
      sky.dispose();
      assets?.dispose();
      handle.dispose();
    },
  });
  window.addEventListener("pagehide", lifecycle.onPageHide);
  window.addEventListener("pageshow", lifecycle.onPageShow);

  // The walk starts only once the terrain is visible; then the collision field is fetched.
  await terrainGate;
  let collision: Awaited<ReturnType<typeof loadCollisionField>>;
  try {
    collision = await loadCollisionField(publicUrl(COLLISION_PATH, base));
  } catch (error) {
    fail(`${t("routeDataFailed")} ${describeError(error)}`);
    return;
  }
  collisionLoaded = true;
  poster.setProgress(progressNow(state.terrain.stats));
  if (debugFlags().has("trail")) {
    trailDebug = createTrailDebug(trail, collision);
    scene.add(trailDebug.object);
  }

  const startFloor = tunnelSurface?.floorAt(start.x, start.z) ?? null;
  const created = createPlayer({
    scene,
    camera,
    canvas,
    heightField: collision,
    groundSurfaces: tunnelSurface === null ? [] : [tunnelSurface],
    enclosures: tunnelSurface === null ? [] : [tunnelSurface],
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
  streamer?.setDetailEnabled(true);
  state.loading.readyMs = Math.round(performance.now());
  poster.hide();
  if (terrainView.outcome === "failed") hud.notify(t("terrainFailed"));
  else hud.notify(null);
  setStatus(t("walkReady"));
  hud.showHints(coarsePointer ? t("hintTouch") : t("hintKeyboard"));
  const requestedAutoWalk = params.get("autowalk");
  if (requestedAutoWalk !== null && requestedAutoWalk !== "") startAutoWalk(requestedAutoWalk);
  loop.start();
}

initCredits();
bootstrap().catch((error: unknown) => {
  fail(`${t("startFailed")} ${describeError(error)}`);
});
