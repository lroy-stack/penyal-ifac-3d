import { Color, PerspectiveCamera, Scene, Vector2 } from "three";
import { type AppState, createAppState } from "./appState";
import { baseUrl, createGltfLoader, type GltfLoaderHandle, publicUrl } from "./core/assets";
import { type FrameSnapshot, FrameStats } from "./core/frameStats";
import { createPageLifecycle } from "./core/lifecycle";
import { createLoop } from "./core/loop";
import { createRenderer } from "./core/renderer";
import { parseTimescale, simulationSteps } from "./core/timescale";
import { createPlayer } from "./player";
import { buildAutoWalkRoute } from "./player/autowalk";
import { MAX_FRAME_DT } from "./player/controller";
import { initCredits } from "./ui/credits";
import { createPerfOverlay, isPerfRequested, type PerfOverlay } from "./ui/perfOverlay";
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
  type TerrainStreamer,
  viewFromCamera,
} from "./world/terrain";
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
  setStatus(message);
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
  const far = cameraFar();
  const camera = new PerspectiveCamera(65, 1, 0.2, far);

  const handle = createRenderer(canvas, (width, height) => {
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  });
  if (!handle.ok) {
    showFatal(handle.message);
    return;
  }
  const { renderer } = handle;

  setStatus("Cargando el recorrido…");
  const coarsePointer = window.matchMedia("(pointer: coarse)").matches;
  const base = baseUrl();
  const manifestUrl = publicUrl(TERRAIN_MANIFEST_PATH, base);

  let collision: Awaited<ReturnType<typeof loadCollisionField>>;
  let trail: Awaited<ReturnType<typeof loadTrail>>;
  let manifest: Awaited<ReturnType<typeof loadTerrainManifest>>;
  let tunnelFile: Awaited<ReturnType<typeof loadTunnel>>;
  try {
    [collision, trail, manifest, tunnelFile] = await Promise.all([
      loadCollisionField(publicUrl(COLLISION_PATH, base)),
      loadTrail(publicUrl(TRAIL_PATH, base)),
      loadTerrainManifest(manifestUrl),
      loadTunnel(publicUrl(TUNNEL_PATH, base)),
    ]);
  } catch (error) {
    handle.dispose();
    showFatal(`No se pudieron cargar los datos del recorrido. ${describeError(error)}`);
    return;
  }

  const params = new URLSearchParams(location.search);
  const corridor = new PolygonCorridor(trail.corridor.polygon.map(([x, z]) => [x, z] as const));
  const start = startAnchor(trail, params.get("start"), corridor).anchor;
  const summit = trail.anchors.summit ?? start;

  const scene = new Scene();
  scene.background = new Color(HORIZON_COLOR);
  scene.fog = createFog(summit);
  const sky = createSky(far * 0.9);
  scene.add(sky.object);
  scene.add(createSea());

  const state: AppState = createAppState();
  state.timescale = parseTimescale(location.search);
  window.__appState = state;

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
    });
    scene.add(streamer.root);
    state.terrain.status = "ready";
    setStatus("Escena lista. Cargando el terreno…");
  } else if (manifest.status === "missing") {
    state.terrain.status = "missing";
    setStatus("Terreno en preparación");
  } else {
    state.terrain.status = "error";
    state.terrain.message = manifest.message;
    setStatus(`El terreno no está disponible. ${manifest.message}`);
  }

  let trailDebug: TrailDebug | null = null;
  if (debugFlags().has("trail")) {
    trailDebug = createTrailDebug(trail, collision);
    scene.add(trailDebug.object);
  }

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
        setStatus("El interior del túnel no está disponible.");
      },
    );
  } else if (tunnelFile.status === "error") {
    setStatus(`El túnel no está disponible. ${tunnelFile.message}`);
  }

  const startFloor = tunnelSurface?.floorAt(start.x, start.z) ?? null;
  const player = createPlayer({
    scene,
    camera,
    canvas,
    heightField: collision,
    groundSurfaces: tunnelSurface === null ? [] : [tunnelSurface],
    enclosures: tunnelSurface === null ? [] : [tunnelSurface],
    corridor,
    start:
      startFloor === null ? { x: start.x, z: start.z } : { x: start.x, z: start.z, y: startFloor },
    startYaw: headingAlongRoute(routePoints(trail), start),
  });

  const startAutoWalk = (target: string): void => {
    try {
      player.startAutoWalk(buildAutoWalkRoute(trail.route.segments, trail.anchors, target));
    } catch (error) {
      setStatus(`No se puede iniciar el paseo automático. ${describeError(error)}`);
    }
  };
  const requestedAutoWalk = params.get("autowalk");
  if (requestedAutoWalk !== null && requestedAutoWalk !== "") startAutoWalk(requestedAutoWalk);

  const reached = new Set<string>();
  const frameStats = new FrameStats();
  const perfOverlay: PerfOverlay | null = isPerfRequested(location.search)
    ? createPerfOverlay()
    : null;
  let lastSnapshot: FrameSnapshot | null = null;
  const drawingBuffer = new Vector2();
  let terrainAnnounced = false;

  const loop = createLoop((dt, rawMs) => {
    for (const step of simulationSteps(dt, state.timescale, MAX_FRAME_DT)) {
      player.update(step);
      if (player.state.autowalkTogglePressed) {
        if (player.state.autowalk.active) player.stopAutoWalk();
        else startAutoWalk(DEFAULT_AUTOWALK_TARGET);
      }
    }
    const feet = player.state.position;
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
    const { position, grounded, cameraMode, yaw, corridorHit, elapsed } = player.state;
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
    Object.assign(state.autowalk, player.state.autowalk);
    state.camera.x = camera.position.x;
    state.camera.y = camera.position.y;
    state.camera.z = camera.position.z;
    state.render.calls = renderer.info.render.calls;
    state.render.triangles = renderer.info.render.triangles;
    if (rawMs !== null) frameStats.push(rawMs);
    if (frameStats.snapshot !== lastSnapshot) {
      lastSnapshot = frameStats.snapshot;
      state.frameStats = lastSnapshot;
      state.frameTimeP95Ms = lastSnapshot?.p95 ?? null;
      perfOverlay?.update(lastSnapshot, state.render);
    }

    if (streamer !== null && state.frames % STATS_INTERVAL_FRAMES === 1) {
      state.terrain.stats = streamer.stats();
      const { farLoaded, pending } = state.terrain.stats;
      if (!terrainAnnounced && farLoaded && pending === 0) {
        terrainAnnounced = true;
        setStatus("Terreno cargado.");
      }
    }
    state.ready = true;
  });
  loop.start();

  const lifecycle = createPageLifecycle({
    suspend: () => loop.stop(),
    resume: () => loop.start(),
    dispose: () => {
      player.dispose();
      streamer?.dispose();
      trailDebug?.dispose();
      perfOverlay?.dispose();
      tunnelView?.dispose();
      tunnelLamp.light.dispose();
      sky.dispose();
      assets?.dispose();
      handle.dispose();
    },
  });
  window.addEventListener("pagehide", lifecycle.onPageHide);
  window.addEventListener("pageshow", lifecycle.onPageShow);
}

initCredits();
bootstrap().catch((error: unknown) => {
  showFatal(`Error al iniciar el Penyal d'Ifac 3D. ${describeError(error)}`);
});
