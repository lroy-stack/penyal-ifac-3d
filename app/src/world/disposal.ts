import { type BufferGeometry, type Material, Mesh, type Object3D, Texture } from "three";

function disposeMaterial(material: Material): void {
  for (const value of Object.values(material)) {
    if (value instanceof Texture) value.dispose();
  }
  material.dispose();
}

/** Frees the GPU resources (geometries, materials and their textures) behind a glTF scene. */
export function disposeObject(object: Object3D): void {
  object.traverse((child) => {
    if (!(child instanceof Mesh)) return;
    (child.geometry as BufferGeometry).dispose();
    const materials = Array.isArray(child.material) ? child.material : [child.material];
    for (const material of materials as Material[]) disposeMaterial(material);
  });
}
