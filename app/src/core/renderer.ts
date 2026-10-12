import { ACESFilmicToneMapping, SRGBColorSpace, WebGLRenderer } from "three";
import type { QualityProfile } from "./quality";

export const WEBGL2_UNAVAILABLE_MESSAGE =
  "Tu navegador o dispositivo no admite WebGL 2, necesario para mostrar el Penyal en 3D. " +
  "Prueba con una versión reciente de Chrome, Firefox, Safari o Edge, y comprueba que la " +
  "aceleración por hardware esté activada.";

export type RendererHandle = {
  readonly ok: true;
  readonly renderer: WebGLRenderer;
  readonly dispose: () => void;
};

export type RendererFailure = {
  readonly ok: false;
  readonly message: string;
};

/** Device pixels per CSS pixel to render at: the screen's, capped, times the profile's scale. */
export function pixelRatioFor(
  devicePixelRatio: number,
  resolution: QualityProfile["resolution"],
): number {
  return Math.min(devicePixelRatio, resolution.maxPixelRatio) * resolution.scale;
}

/**
 * Probes with a throwaway canvas and releases its context right away: browsers cap the number
 * of live WebGL contexts, and an unreferenced probe would keep one alive until GC.
 */
export function isWebGL2Available(): boolean {
  const gl = document.createElement("canvas").getContext("webgl2");
  if (gl === null) return false;
  gl.getExtension("WEBGL_lose_context")?.loseContext();
  return true;
}

export type RendererOptions = {
  /** Multisampling is on for fine pointers only; it cannot change after creation. */
  readonly coarsePointer: boolean;
  /** Read on every resize, so a new profile applies at the next one. */
  readonly quality: { readonly current: QualityProfile };
};

/**
 * The WebGL 2 context the renderer draws into. three r186 always asks the browser for an alpha
 * channel and only clears it to 1, so any fragment that writes alpha < 1 makes the canvas
 * translucent over the page. Alpha-to-coverage (the vegetation) writes its coverage there: foliage
 * edges and thin crowns showed the white page through. An opaque buffer has no alpha to leak.
 */
export function contextAttributesFor(coarsePointer: boolean): WebGLContextAttributes {
  return {
    alpha: false,
    antialias: !coarsePointer,
    depth: true,
    stencil: false,
    premultipliedAlpha: true,
    preserveDrawingBuffer: false,
    powerPreference: "high-performance",
  };
}

export function createRenderer(
  canvas: HTMLCanvasElement,
  onResize: (width: number, height: number) => void,
  options: RendererOptions,
): RendererHandle | RendererFailure {
  if (!isWebGL2Available()) {
    return { ok: false, message: WEBGL2_UNAVAILABLE_MESSAGE };
  }

  const { coarsePointer, quality } = options;

  let renderer: WebGLRenderer;
  try {
    const context = canvas.getContext("webgl2", contextAttributesFor(coarsePointer));
    if (context === null) return { ok: false, message: WEBGL2_UNAVAILABLE_MESSAGE };
    renderer = new WebGLRenderer({ canvas, context });
  } catch {
    return { ok: false, message: WEBGL2_UNAVAILABLE_MESSAGE };
  }

  renderer.outputColorSpace = SRGBColorSpace;
  // ACES keeps sunlit limestone and sky from clipping to white; AgX would desaturate the
  // warm rock and vegetation tones this scene relies on.
  renderer.toneMapping = ACESFilmicToneMapping;

  const resize = (): void => {
    const width = Math.max(1, canvas.clientWidth);
    const height = Math.max(1, canvas.clientHeight);
    renderer.setPixelRatio(pixelRatioFor(window.devicePixelRatio, quality.current.resolution));
    renderer.setSize(width, height, false);
    onResize(width, height);
  };

  const observer = new ResizeObserver(resize);
  observer.observe(canvas);
  resize();

  return {
    ok: true,
    renderer,
    dispose: () => {
      observer.disconnect();
      renderer.dispose();
    },
  };
}
