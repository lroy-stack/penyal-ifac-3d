import { ACESFilmicToneMapping, SRGBColorSpace, WebGLRenderer } from "three";

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

export function maxPixelRatio(coarsePointer: boolean): number {
  return coarsePointer ? 1.5 : 2;
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

export function createRenderer(
  canvas: HTMLCanvasElement,
  onResize: (width: number, height: number) => void,
): RendererHandle | RendererFailure {
  if (!isWebGL2Available()) {
    return { ok: false, message: WEBGL2_UNAVAILABLE_MESSAGE };
  }

  const coarsePointer = window.matchMedia("(pointer: coarse)").matches;

  let renderer: WebGLRenderer;
  try {
    renderer = new WebGLRenderer({
      canvas,
      antialias: !coarsePointer,
      powerPreference: "high-performance",
    });
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
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, maxPixelRatio(coarsePointer)));
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
