import {
  type BufferGeometry,
  type Material,
  Mesh,
  type Object3D,
  PointLight,
  Texture,
} from "three";
import type { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

/** Intensity of the lamp that lights the tunnel interior (the hemisphere light barely reaches it). */
export const TUNNEL_LAMP_INTENSITY = 7;
/** Reach (m) of the tunnel lamp. */
export const TUNNEL_LAMP_DISTANCE = 14;

export type TunnelView = {
  readonly object: Object3D;
  readonly dispose: () => void;
};

/** Loads the interior shell (`tunnel.glb`, visual only, inward-facing). */
export async function loadTunnelView(loader: GLTFLoader, url: string): Promise<TunnelView> {
  const gltf = await loader.loadAsync(url);
  const object = gltf.scene;
  object.traverse((child) => {
    if (!(child instanceof Mesh)) return;
    const geometry = child.geometry as BufferGeometry;
    if (geometry.boundingSphere === null) geometry.computeBoundingSphere();
  });
  object.updateMatrixWorld(true);
  return {
    object,
    dispose: () => {
      object.traverse((child) => {
        if (!(child instanceof Mesh)) return;
        (child.geometry as BufferGeometry).dispose();
        const materials = Array.isArray(child.material) ? child.material : [child.material];
        for (const material of materials as Material[]) {
          for (const value of Object.values(material))
            if (value instanceof Texture) value.dispose();
          material.dispose();
        }
      });
    },
  };
}

export type TunnelLamp = {
  readonly light: PointLight;
  /** Moves the lamp to the player and switches it on only while the player is in the tunnel. */
  readonly update: (position: { x: number; y: number; z: number }, inside: boolean) => void;
};

/**
 * A lamp that travels with the player. The light count stays constant (intensity 0 outside) so
 * the materials do not recompile when entering the tunnel.
 */
export function createTunnelLamp(): TunnelLamp {
  const light = new PointLight(0xffe8c4, 0, TUNNEL_LAMP_DISTANCE, 1.6);
  return {
    light,
    update: (position, inside) => {
      light.position.set(position.x, position.y + 1.2, position.z);
      light.intensity = inside ? TUNNEL_LAMP_INTENSITY : 0;
    },
  };
}
