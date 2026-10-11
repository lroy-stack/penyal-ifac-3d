/**
 * Minimal binary glTF writer for end-to-end tests: one flat, lit grid with a base colour.
 * These are synthetic fixtures served through request interception only; they are never written
 * to `public/` and are not terrain data.
 */
export function flatGridGlb(options: {
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
  y: number;
  cells: number;
  color: [number, number, number];
}): Buffer {
  const { minX, maxX, minZ, maxZ, y, cells, color } = options;
  const side = cells + 1;
  const positions = new Float32Array(side * side * 3);
  const normals = new Float32Array(side * side * 3);
  for (let j = 0; j < side; j++) {
    for (let i = 0; i < side; i++) {
      const k = (j * side + i) * 3;
      positions.set([minX + ((maxX - minX) * i) / cells, y, minZ + ((maxZ - minZ) * j) / cells], k);
      normals.set([0, 1, 0], k);
    }
  }
  const indices = new Uint16Array(cells * cells * 6);
  let n = 0;
  for (let j = 0; j < cells; j++) {
    for (let i = 0; i < cells; i++) {
      const a = j * side + i;
      // Counter-clockwise seen from +Y (FrontSide faces up).
      indices.set([a, a + side, a + 1, a + 1, a + side, a + side + 1], n);
      n += 6;
    }
  }

  const positionBytes = Buffer.from(positions.buffer);
  const normalBytes = Buffer.from(normals.buffer);
  const indexBytes = Buffer.from(indices.buffer);
  const pad = (buffer: Buffer): Buffer =>
    Buffer.concat([buffer, Buffer.alloc((4 - (buffer.length % 4)) % 4)]);
  const binary = Buffer.concat([pad(positionBytes), pad(normalBytes), pad(indexBytes)]);

  const json = {
    asset: { version: "2.0" },
    scene: 0,
    scenes: [{ nodes: [0] }],
    nodes: [{ mesh: 0 }],
    meshes: [{ primitives: [{ attributes: { POSITION: 0, NORMAL: 1 }, indices: 2, material: 0 }] }],
    materials: [
      {
        pbrMetallicRoughness: {
          baseColorFactor: [...color, 1],
          metallicFactor: 0,
          roughnessFactor: 1,
        },
      },
    ],
    accessors: [
      {
        bufferView: 0,
        componentType: 5126,
        count: side * side,
        type: "VEC3",
        min: [minX, y, minZ],
        max: [maxX, y, maxZ],
      },
      { bufferView: 1, componentType: 5126, count: side * side, type: "VEC3" },
      { bufferView: 2, componentType: 5123, count: indices.length, type: "SCALAR" },
    ],
    bufferViews: [
      { buffer: 0, byteOffset: 0, byteLength: positionBytes.length, target: 34962 },
      {
        buffer: 0,
        byteOffset: pad(positionBytes).length,
        byteLength: normalBytes.length,
        target: 34962,
      },
      {
        buffer: 0,
        byteOffset: pad(positionBytes).length + pad(normalBytes).length,
        byteLength: indexBytes.length,
        target: 34963,
      },
    ],
    buffers: [{ byteLength: binary.length }],
  };

  const jsonBytes = Buffer.from(JSON.stringify(json));
  const jsonChunk = Buffer.concat([
    jsonBytes,
    Buffer.alloc((4 - (jsonBytes.length % 4)) % 4, 0x20),
  ]);
  const header = Buffer.alloc(12);
  header.write("glTF", 0, "ascii");
  header.writeUInt32LE(2, 4);
  header.writeUInt32LE(12 + 8 + jsonChunk.length + 8 + binary.length, 8);
  const chunkHeader = (length: number, type: string): Buffer => {
    const out = Buffer.alloc(8);
    out.writeUInt32LE(length, 0);
    out.write(type, 4, "ascii");
    return out;
  };
  return Buffer.concat([
    header,
    chunkHeader(jsonChunk.length, "JSON"),
    jsonChunk,
    chunkHeader(binary.length, "BIN\0"),
    binary,
  ]);
}
