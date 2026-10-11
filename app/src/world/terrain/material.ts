import type { IUniform, Material, Texture, WebGLProgramParametersWithUniforms } from "three";
import { MeshStandardMaterial } from "three";

/**
 * Terrain detail shading, patched into the glTF `MeshStandardMaterial` of every tile with
 * `onBeforeCompile` so three keeps doing lighting, fog and colour management. All tiles share one
 * program (same patch, same cache key, uniforms shared by reference).
 *
 * - Cliffs: where the surface is steeper than `CLIFF_START_DEG` the top-down orthophoto is a
 *   vertical smear, so the albedo is replaced, fully from `CLIFF_FULL_DEG`, by triplanar
 *   procedural limestone tinted with the orthophoto's local average (16x16 cells per tile, sampled
 *   from a high mip) so the hue stays that of the real rock. Structure: horizontal strata plus
 *   grain and cracks, from value noise in world space. This is an approximation, not surveyed
 *   geometry or photography.
 * - Near ground: world-space noise modulates albedo by +-`GROUND_ALBEDO_AMPLITUDE` and bumps the
 *   normal, fading out between `NEAR_FADE_START_M` and `NEAR_FADE_END_M` from the camera. Every
 *   noise octave also fades out as its wavelength approaches the pixel footprint, so it cannot
 *   shimmer.
 *
 * - Real maps: once the CC0 marble maps (`detailTextures.ts`) are loaded, `uRockMode` switches
 *   both layers from the procedural noise to those maps (triplanar on cliffs, planar on the
 *   ground), keeping the procedural path as the fallback while they load or when they fail. The
 *   map only supplies structure: its luminance relative to its own mean multiplies the
 *   orthophoto's local colour, so the hue stays that of the real rock, not of the marble.
 */

export const CLIFF_START_DEG = 45;
export const CLIFF_FULL_DEG = 55;
export const NEAR_FADE_START_M = 14;
export const NEAR_FADE_END_M = 30;
export const GROUND_ALBEDO_AMPLITUDE = 0.1;
export const ROCK_ALBEDO_AMPLITUDE = 0.35;
export const GROUND_RELIEF_M = 0.02;
export const ROCK_RELIEF_M = 0.06;
/** The orthophoto average is read at `log2(textureSize) - this` : 2^4 = 16 cells per tile side. */
export const AVERAGE_MIP_DROP = 4;

const DEG = Math.PI / 180;

function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = Math.min(1, Math.max(0, (x - edge0) / (edge1 - edge0)));
  return t * t * (3 - 2 * t);
}

/**
 * Share of the procedural rock (0 orthophoto, 1 rock) for a unit surface normal with vertical
 * component `normalY`. Smooth between 45 and 55 degrees from the horizontal. The GLSL uses the
 * same constants and the same smoothstep.
 */
export function cliffWeight(normalY: number): number {
  const upper = Math.cos(CLIFF_START_DEG * DEG);
  const lower = Math.cos(CLIFF_FULL_DEG * DEG);
  return 1 - smoothstep(lower, upper, normalY);
}

/** Weight (0..1) of the near-ground detail at `distance` metres from the camera. */
export function nearDetailWeight(distance: number): number {
  return 1 - smoothstep(NEAR_FADE_START_M, NEAR_FADE_END_M, distance);
}

/** Real-world size (m) of one repeat of the marble maps. */
export const ROCK_TILE_M = 20;
/** Ground detail repeats this many times faster than the cliff maps (6.3 m per repeat). */
export const GROUND_TILE_FACTOR = 3.17;
export const ROCK_NORMAL_STRENGTH = 0.8;

export type TerrainDetailUniforms = {
  readonly uTerrainCliffStrength: IUniform<number>;
  readonly uTerrainGroundStrength: IUniform<number>;
  /** 0: procedural noise; 1: the maps below are loaded and used. */
  readonly uRockMode: IUniform<number>;
  readonly uRockDiff: IUniform<Texture | null>;
  readonly uRockNor: IUniform<Texture | null>;
  readonly uRockArm: IUniform<Texture | null>;
};

/** Uniforms shared by every tile material; both default to full strength. */
export function createTerrainDetailUniforms(): TerrainDetailUniforms {
  return {
    uTerrainCliffStrength: { value: 1 },
    uTerrainGroundStrength: { value: 1 },
    uRockMode: { value: 0 },
    uRockDiff: { value: null },
    uRockNor: { value: null },
    uRockArm: { value: null },
  };
}

const f = (value: number): string => value.toFixed(6);

const VERTEX_PARS = /* glsl */ `
varying highp vec3 vTerrainWorldPos;
varying highp vec3 vTerrainWorldNormal;
`;

const VERTEX_END = /* glsl */ `
	vTerrainWorldPos = ( modelMatrix * vec4( transformed, 1.0 ) ).xyz;
	vTerrainWorldNormal = mat3( modelMatrix ) * objectNormal;
`;

const FRAGMENT_PARS = /* glsl */ `
varying highp vec3 vTerrainWorldPos;
varying highp vec3 vTerrainWorldNormal;
uniform float uTerrainCliffStrength;
uniform float uTerrainGroundStrength;
uniform float uRockMode;
uniform sampler2D uRockDiff;
uniform sampler2D uRockNor;
uniform sampler2D uRockArm;

float tHash( vec2 p ) {
	vec3 p3 = fract( vec3( p.xyx ) * 0.1031 );
	p3 += dot( p3, p3.yzx + 33.33 );
	return fract( ( p3.x + p3.y ) * p3.z );
}

// Value noise in [-1, 1].
float tNoise( vec2 p ) {
	vec2 i = floor( p );
	vec2 fr = fract( p );
	vec2 u = fr * fr * ( 3.0 - 2.0 * fr );
	float a = tHash( i );
	float b = tHash( i + vec2( 1.0, 0.0 ) );
	float c = tHash( i + vec2( 0.0, 1.0 ) );
	float d = tHash( i + vec2( 1.0, 1.0 ) );
	return mix( mix( a, b, u.x ), mix( c, d, u.x ), u.y ) * 2.0 - 1.0;
}

// Share of an octave to keep when one cell spans 'cellMetres' and a pixel spans 'footprint'.
float tOctaveFade( float footprint, float cellMetres ) {
	return 1.0 - smoothstep( 0.2, 0.5, footprint / cellMetres );
}

// One triplanar face of the rock: 'p' is in metres, 'cells' the cell size in metres per axis.
// Returns x = albedo modulation in [-1, 1], y = relief in [-1, 1].
vec2 tRockPlane( vec2 p, vec2 cells, float footprint ) {
	float strata = tNoise( p / ( cells * vec2( 3.0, 1.0 ) ) ) * tOctaveFade( footprint, cells.y );
	float body = tNoise( p / ( cells * vec2( 1.0, 0.5 ) ) ) * tOctaveFade( footprint, cells.y * 0.5 );
	float crack = ( 1.0 - abs( tNoise( p / ( cells * vec2( 0.5, 0.25 ) ) ) ) ) * 2.0 - 1.0;
	crack *= tOctaveFade( footprint, cells.y * 0.25 );
	float lum = 0.45 * strata + 0.3 * body + 0.25 * crack;
	return vec2( lum, 0.5 * strata + 0.3 * body + 0.2 * crack );
}

// Triplanar limestone: horizontal strata on the vertical faces, isotropic on the flat ones.
vec2 terrainRock( vec3 wp, vec3 n, float footprint ) {
	vec3 w = pow( abs( n ), vec3( 4.0 ) );
	w /= ( w.x + w.y + w.z );
	vec2 r = vec2( 0.0 );
	if ( w.x > 0.02 ) r += w.x * tRockPlane( vec2( wp.z, wp.y ), vec2( 0.9, 0.5 ), footprint );
	if ( w.z > 0.02 ) r += w.z * tRockPlane( vec2( wp.x + 17.3, wp.y ), vec2( 0.9, 0.5 ), footprint );
	if ( w.y > 0.02 ) r += w.y * tRockPlane( wp.xz + 41.7, vec2( 0.7 ), footprint );
	return r;
}

// Ground detail: x = albedo modulation in [-1, 1], y = relief in [-1, 1].
vec2 terrainGround( vec2 p, float footprint ) {
	float coarse = tNoise( p / 2.0 ) * tOctaveFade( footprint, 2.0 );
	float mid = tNoise( p / 0.45 + 7.1 ) * tOctaveFade( footprint, 0.45 );
	float fine = tNoise( p / 0.1 + 3.7 ) * tOctaveFade( footprint, 0.1 );
	float v = 0.45 * coarse + 0.35 * mid + 0.2 * fine;
	return vec2( v, 0.2 * coarse + 0.4 * mid + 0.4 * fine );
}

// Triplanar lookup with explicit derivatives, so it is safe inside non-uniform branches.
vec3 tTriplanar( sampler2D tex, vec3 wp, vec3 w, float s, vec3 dx, vec3 dy ) {
	return textureGrad( tex, wp.zy * s, dx.zy * s, dy.zy * s ).rgb * w.x
		+ textureGrad( tex, wp.xz * s, dx.xz * s, dy.xz * s ).rgb * w.y
		+ textureGrad( tex, wp.xy * s, dx.xy * s, dy.xy * s ).rgb * w.z;
}

// Whiteout-blended triplanar normal map (OpenGL convention), returned in world space.
vec3 tTriplanarNormal( sampler2D tex, vec3 wp, vec3 n, vec3 w, float s, vec3 dx, vec3 dy, float strength ) {
	vec3 tx = textureGrad( tex, wp.zy * s, dx.zy * s, dy.zy * s ).xyz * 2.0 - 1.0;
	vec3 ty = textureGrad( tex, wp.xz * s, dx.xz * s, dy.xz * s ).xyz * 2.0 - 1.0;
	vec3 tz = textureGrad( tex, wp.xy * s, dx.xy * s, dy.xy * s ).xyz * 2.0 - 1.0;
	tx = vec3( tx.xy * strength + n.zy, abs( tx.z ) * n.x );
	ty = vec3( ty.xy * strength + n.xz, abs( ty.z ) * n.y );
	tz = vec3( tz.xy * strength + n.xy, abs( tz.z ) * n.z );
	return normalize( tx.zyx * w.x + ty.xzy * w.y + tz.xyz * w.z );
}

float tLuma( vec3 c ) {
	return dot( c, vec3( 0.2126, 0.7152, 0.0722 ) );
}

vec3 terrainBump( vec3 surfPos, vec3 surfNormal, float height ) {
	vec3 dpdx = dFdx( surfPos );
	vec3 dpdy = dFdy( surfPos );
	float dhx = dFdx( height );
	float dhy = dFdy( height );
	vec3 r1 = cross( dpdy, surfNormal );
	vec3 r2 = cross( surfNormal, dpdx );
	float det = dot( dpdx, r1 );
	vec3 grad = sign( det ) * ( dhx * r1 + dhy * r2 );
	return normalize( abs( det ) * surfNormal - grad );
}
`;

const FRAGMENT_ALBEDO = /* glsl */ `
	float tDistance = length( vViewPosition );
	vec3 tWorldNormal = normalize( vTerrainWorldNormal );
	vec3 tDx = dFdx( vTerrainWorldPos );
	vec3 tDy = dFdy( vTerrainWorldPos );
	float tFootprint = max( max( length( tDx ), length( tDy ) ), 1e-4 );
	float tUpper = ${f(Math.cos(CLIFF_START_DEG * DEG))};
	float tLower = ${f(Math.cos(CLIFF_FULL_DEG * DEG))};
	float tCliff = ( 1.0 - smoothstep( tLower, tUpper, tWorldNormal.y ) ) * uTerrainCliffStrength;
	float tNear = ( 1.0 - smoothstep( ${f(NEAR_FADE_START_M)}, ${f(NEAR_FADE_END_M)}, tDistance ) )
		* uTerrainGroundStrength * ( 1.0 - tCliff );
	float tRelief = 0.0;
	float tRoughness = 0.0;
	float tRoughnessWeight = 0.0;
	vec3 tMapNormal = tWorldNormal;
	float tMapNormalWeight = 0.0;
	vec3 tRockW = pow( abs( tWorldNormal ), vec3( 4.0 ) );
	tRockW /= ( tRockW.x + tRockW.y + tRockW.z );
	float tRockMean = uRockMode > 0.5 ? tLuma( textureLod( uRockDiff, vec2( 0.5 ), 16.0 ).rgb ) + 1e-4 : 1.0;
	float tRockScale = ${f(1 / ROCK_TILE_M)};
	#ifdef USE_MAP
	if ( tCliff > 0.0 ) {
		float tAverageLod = log2( float( textureSize( map, 0 ).x ) ) - ${f(AVERAGE_MIP_DROP)};
		vec3 tAverage = textureLod( map, vMapUv, tAverageLod ).rgb;
		vec3 tRockColor;
		if ( uRockMode > 0.5 ) {
			float lumaA = tLuma( tTriplanar( uRockDiff, vTerrainWorldPos, tRockW, tRockScale, tDx, tDy ) ) / tRockMean;
			float lumaB = tLuma( tTriplanar( uRockDiff, vTerrainWorldPos + 13.7, tRockW, tRockScale * ${f(GROUND_TILE_FACTOR)}, tDx, tDy ) ) / tRockMean;
			vec3 arm = tTriplanar( uRockArm, vTerrainWorldPos, tRockW, tRockScale, tDx, tDy );
			float ratio = clamp( mix( lumaA, lumaA * lumaB, 0.5 ), 0.25, 2.0 );
			tRockColor = tAverage * ratio * mix( 1.0, arm.r, 0.7 );
			tRoughness += tCliff * arm.g;
			tRoughnessWeight += tCliff;
			tMapNormal = tTriplanarNormal( uRockNor, vTerrainWorldPos, tWorldNormal, tRockW, tRockScale, tDx, tDy, ${f(ROCK_NORMAL_STRENGTH)} );
			tMapNormalWeight = tCliff;
		} else {
			vec2 tRock = terrainRock( vTerrainWorldPos, tWorldNormal, tFootprint );
			tRockColor = tAverage * ( 1.0 + ${f(ROCK_ALBEDO_AMPLITUDE)} * tRock.x );
			tRelief += tCliff * ${f(ROCK_RELIEF_M)} * tRock.y;
		}
		diffuseColor.rgb = mix( diffuseColor.rgb, tRockColor, tCliff );
	}
	#endif
	if ( tNear > 0.0 ) {
		if ( uRockMode > 0.5 ) {
			float tGroundScale = tRockScale * ${f(GROUND_TILE_FACTOR)};
			vec2 gUv = vTerrainWorldPos.xz * tGroundScale;
			vec2 gDx = tDx.xz * tGroundScale;
			vec2 gDy = tDy.xz * tGroundScale;
			float luma = tLuma( textureGrad( uRockDiff, gUv, gDx, gDy ).rgb ) / tRockMean;
			float g = clamp( ( luma - 1.0 ) / 0.6, -1.0, 1.0 );
			diffuseColor.rgb *= 1.0 + ${f(GROUND_ALBEDO_AMPLITUDE)} * tNear * g;
			vec3 gm = textureGrad( uRockNor, gUv, gDx, gDy ).xyz * 2.0 - 1.0;
			vec3 gN = normalize( vec3( gm.x * ${f(ROCK_NORMAL_STRENGTH)} + tWorldNormal.x, abs( gm.z ) * tWorldNormal.y, gm.y * ${f(ROCK_NORMAL_STRENGTH)} + tWorldNormal.z ) );
			tMapNormal = normalize( mix( tMapNormal, gN, tNear ) );
			tMapNormalWeight = max( tMapNormalWeight, tNear * 0.6 );
		} else {
			vec2 tGround = terrainGround( vTerrainWorldPos.xz, tFootprint );
			diffuseColor.rgb *= 1.0 + ${f(GROUND_ALBEDO_AMPLITUDE)} * tNear * tGround.x;
			tRelief += tNear * ${f(GROUND_RELIEF_M)} * tGround.y;
		}
	}
`;

const FRAGMENT_ROUGHNESS = /* glsl */ `
	roughnessFactor = mix( roughnessFactor, tRoughness, clamp( tRoughnessWeight, 0.0, 1.0 ) );
`;

const FRAGMENT_NORMAL = /* glsl */ `
	normal = normalize( mix( normal, normalize( mat3( viewMatrix ) * tMapNormal ), tMapNormalWeight ) );
	normal = terrainBump( - vViewPosition, normal, tRelief );
`;

/** Identifies the patch in three's program cache; bump it whenever the GLSL above changes. */
export const TERRAIN_PROGRAM_KEY = "penyal-terrain-detail-v4";

function replaceOnce(
  source: string,
  chunk: string,
  addition: string,
  where: "after" | "before",
): string {
  const token = `#include <${chunk}>`;
  if (!source.includes(token)) {
    throw new Error(
      `three shader is missing #include <${chunk}>; the terrain patch needs updating.`,
    );
  }
  return where === "after"
    ? source.replace(token, `${token}\n${addition}`)
    : source.replace(token, `${addition}\n${token}`);
}

/** Pure text transform of the two shader stages; exported for tests. */
export function patchTerrainShader(
  vertexShader: string,
  fragmentShader: string,
): {
  vertexShader: string;
  fragmentShader: string;
} {
  let vertex = replaceOnce(vertexShader, "common", VERTEX_PARS, "after");
  vertex = replaceOnce(vertex, "fog_vertex", VERTEX_END, "after");
  let fragment = replaceOnce(fragmentShader, "common", FRAGMENT_PARS, "after");
  fragment = replaceOnce(fragment, "color_fragment", FRAGMENT_ALBEDO, "after");
  fragment = replaceOnce(fragment, "roughnessmap_fragment", FRAGMENT_ROUGHNESS, "after");
  fragment = replaceOnce(fragment, "normal_fragment_maps", FRAGMENT_NORMAL, "after");
  return { vertexShader: vertex, fragmentShader: fragment };
}

/**
 * Adds the detail shading to a glTF tile material. Only `MeshStandardMaterial` is patched, and
 * only when it has a base colour texture (the cliff average needs it).
 */
export function applyTerrainDetail(material: Material, uniforms: TerrainDetailUniforms): void {
  if (!(material instanceof MeshStandardMaterial)) return;
  material.onBeforeCompile = (shader: WebGLProgramParametersWithUniforms) => {
    Object.assign(shader.uniforms, uniforms);
    const patched = patchTerrainShader(shader.vertexShader, shader.fragmentShader);
    shader.vertexShader = patched.vertexShader;
    shader.fragmentShader = patched.fragmentShader;
  };
  material.customProgramCacheKey = () => TERRAIN_PROGRAM_KEY;
  material.needsUpdate = true;
}
