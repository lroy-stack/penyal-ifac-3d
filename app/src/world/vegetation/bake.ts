import { type BufferGeometry, Float32BufferAttribute, type Matrix4 } from "three";

/**
 * A copy of `geometry` with `matrix` applied. The vegetation GLBs use KHR_mesh_quantization: the
 * positions and normals are normalised integers that the node's scale and translation bring back
 * to metres, so the matrix cannot be applied to them in place (the result would be clamped to
 * [-1, 1]). They are widened to Float32 first.
 */
export function bakeTransform(geometry: BufferGeometry, matrix: Matrix4): BufferGeometry {
  const baked = geometry.clone();
  for (const name of ["position", "normal"] as const) {
    const source = baked.getAttribute(name);
    if (source === undefined) continue;
    const widened = new Float32BufferAttribute(source.count * 3, 3);
    for (let i = 0; i < source.count; i++) {
      widened.setXYZ(i, source.getX(i), source.getY(i), source.getZ(i));
    }
    baked.setAttribute(name, widened);
  }
  baked.applyMatrix4(matrix);
  return baked;
}
