import {
  BufferGeometry,
  CanvasTexture,
  Float32BufferAttribute,
  Group,
  Line,
  LineBasicMaterial,
  LineLoop,
  Mesh,
  MeshBasicMaterial,
  SphereGeometry,
  Sprite,
  SpriteMaterial,
} from "three";
import type { HeightField } from "./ground";
import type { Trail } from "./trail";

/** Lines float this far (m) above the surface so they are not buried by the ground. */
export const LINE_LIFT = 0.4;
const ROUTE_COLOR = 0xff2020;
const CORRIDOR_COLOR = 0xffd400;
const ANCHOR_COLOR = 0x20e0ff;

/** Flat xyz positions of each route segment, lifted above the (draped) route heights. */
export function routeLinePositions(trail: Trail): Float32Array[] {
  return trail.route.segments.map((segment) => {
    const out = new Float32Array(segment.points.length * 3);
    segment.points.forEach(([x, y, z], i) => {
      out.set([x, y + LINE_LIFT, z], i * 3);
    });
    return out;
  });
}

/** Flat xyz positions of the corridor outline, draped on `heightField` (0 where it has no data). */
export function corridorLinePositions(trail: Trail, heightField: HeightField): Float32Array {
  const polygon = trail.corridor.polygon;
  const out = new Float32Array(polygon.length * 3);
  polygon.forEach(([x, z], i) => {
    out.set([x, (heightField.heightAt(x, z) ?? 0) + LINE_LIFT, z], i * 3);
  });
  return out;
}

function lineGeometry(positions: Float32Array): BufferGeometry {
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new Float32BufferAttribute(positions, 3));
  return geometry;
}

function labelSprite(text: string): Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 96;
  const context = canvas.getContext("2d");
  if (context === null) throw new Error("A 2D canvas context is needed for debug labels.");
  context.font = "bold 48px system-ui, sans-serif";
  context.textBaseline = "middle";
  context.lineWidth = 8;
  context.strokeStyle = "#000";
  context.strokeText(text, 8, 48);
  context.fillStyle = "#fff";
  context.fillText(text, 8, 48);
  const sprite = new Sprite(
    new SpriteMaterial({
      map: new CanvasTexture(canvas),
      depthTest: false,
      fog: false,
      transparent: true,
    }),
  );
  sprite.scale.set(48, 9, 1);
  sprite.center.set(0, 0);
  sprite.renderOrder = 1001;
  return sprite;
}

export type TrailDebug = { readonly object: Group; readonly dispose: () => void };

/**
 * `?debug=trail`: the OSM route (red), the corridor outline (yellow) and the anchors (labelled
 * markers), drawn over the terrain without depth testing. This is how OSM and the DEM are
 * checked against each other by eye.
 */
export function createTrailDebug(trail: Trail, heightField: HeightField): TrailDebug {
  const group = new Group();
  group.name = "trail-debug";
  const geometries: BufferGeometry[] = [];
  const materials: (LineBasicMaterial | MeshBasicMaterial | SpriteMaterial)[] = [];

  const routeMaterial = new LineBasicMaterial({ color: ROUTE_COLOR, depthTest: false, fog: false });
  const corridorMaterial = new LineBasicMaterial({
    color: CORRIDOR_COLOR,
    depthTest: false,
    fog: false,
  });
  materials.push(routeMaterial, corridorMaterial);

  for (const positions of routeLinePositions(trail)) {
    const geometry = lineGeometry(positions);
    geometries.push(geometry);
    const line = new Line(geometry, routeMaterial);
    line.renderOrder = 1000;
    line.frustumCulled = false;
    group.add(line);
  }

  const corridorGeometry = lineGeometry(corridorLinePositions(trail, heightField));
  geometries.push(corridorGeometry);
  const outline = new LineLoop(corridorGeometry, corridorMaterial);
  outline.renderOrder = 1000;
  outline.frustumCulled = false;
  group.add(outline);

  const markerGeometry = new SphereGeometry(1.5, 12, 8);
  const markerMaterial = new MeshBasicMaterial({
    color: ANCHOR_COLOR,
    depthTest: false,
    fog: false,
  });
  geometries.push(markerGeometry);
  materials.push(markerMaterial);
  for (const [name, anchor] of Object.entries(trail.anchors)) {
    const marker = new Mesh(markerGeometry, markerMaterial);
    marker.position.set(anchor.x, anchor.y + 2, anchor.z);
    marker.renderOrder = 1000;
    marker.name = `anchor:${name}`;
    group.add(marker);
    const label = labelSprite(name);
    label.position.set(anchor.x, anchor.y + 4, anchor.z);
    group.add(label);
    materials.push(label.material);
  }

  return {
    object: group,
    dispose: () => {
      for (const geometry of geometries) geometry.dispose();
      for (const material of materials) {
        if (material instanceof SpriteMaterial) material.map?.dispose();
        material.dispose();
      }
    },
  };
}
