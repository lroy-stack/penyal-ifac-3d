"""``penyal`` command line entry point."""

import argparse
import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import shapely

from penyal_pipeline import (
    artefacts,
    buildings,
    dem,
    doctor,
    fetch,
    ortho,
    provenance,
    structures,
    surfaces,
    tiles,
    trail,
    tunnel,
    tunnel_geometry,
    vegetation,
)
from penyal_pipeline.catalog import CatalogError, load_catalog, select_sources
from penyal_pipeline.nat64 import Nat64Resolver, parse_prefix
from penyal_pipeline.paths import (
    BUILD_DIR,
    GENERATED_DIR,
    PINE_BUILD,
    PINE_GENERATED,
    PLANTS_BUILD,
    SPIKE_GLB,
    TERRAIN_BUILD_DIR,
    TERRAIN_GENERATED_DIR,
    TRAIL_BUILD,
    TRAIL_GENERATED,
)
from penyal_pipeline.rawdata import RawDataError, locate
from penyal_pipeline.render import format_table


def _cmd_doctor(args: argparse.Namespace) -> int:
    results = doctor.run_checks()
    print(doctor.render_json(results) if args.json else doctor.render_table(results))
    return doctor.exit_code(results)


def _cmd_fetch(args: argparse.Namespace) -> int:
    sources = select_sources(load_catalog(), args.phase, args.only)
    if args.dry_run:
        headers = ["ID", "FILE", "HOST", "EXPECTED SIZE", "LICENCE"]
        print(format_table(headers, fetch.plan_rows(sources)))
        return 0
    if args.verify:
        problems = fetch.verify_sources(sources)
        for problem in problems:
            print(f"FAIL {problem}")
        if not problems:
            print(f"verified {len(sources)} source(s): all files match manifest.lock.json")
        return 1 if problems else 0
    resolver: Nat64Resolver | None = None
    if args.nat64_prefix:
        try:
            resolver = Nat64Resolver(parse_prefix(args.nat64_prefix))
        except ValueError as exc:
            print(f"error: --nat64-prefix: {exc}", file=sys.stderr)
            return 2
        print(f"connecting through NAT64 prefix {resolver.prefix}", file=sys.stderr)
    errors = fetch.run_fetch(
        sources,
        downloader=fetch.Downloader(nat64=resolver),
        refresh=args.refresh,
        update_lock=args.update_lock,
    )
    for error in errors:
        print(f"FAIL {error}")
    return 1 if errors else 0


def _cmd_spike(args: argparse.Namespace) -> int:
    from penyal_pipeline.blender import spike

    out = spike.run_spike(args.out)
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


def _cmd_dem(args: argparse.Namespace) -> int:
    mdt, hydrography = dem.locate_inputs()
    build = dem.build_dem(mdt, hydrography)
    dem.write_dem(TERRAIN_BUILD_DIR, build.grid, build.source, build.sea_fill)
    osm = trail.load_osm(locate(trail.OSM_SOURCE_ID, trail.OSM_FILE).path)
    curated = tunnel.load_curated()
    bounds = trail.walkable_bounds(osm, tunnel=curated.trail_spec())
    features = tunnel.terrain_features(osm, build.grid, curated)
    collision = dem.crop(features.carve.apply(build.grid), bounds)
    collision_meta = dem.write_collision(
        TERRAIN_GENERATED_DIR,
        collision,
        build.source,
        build.sea_fill,
        artefacts.provenance("collision"),
    )
    summit = dem.summit_cells(build.grid)
    print(
        f"dem: {build.grid.width}x{build.grid.height} cells, "
        f"{build.meta['minHeight']} .. {build.meta['maxHeight']} m, "
        f"sea fill {build.sea_fill['seaCells']} cells "
        f"(+{build.sea_fill['nodataCells']} nodata) at {dem.SEA_FILL_HEIGHT} m"
    )
    print(f"dem max {summit['height']:.2f} m at E {summit['e']:.1f} N {summit['n']:.1f}")
    print(
        f"collision: {collision_meta['width']}x{collision_meta['height']} cells, "
        f"x0 {collision_meta['x0']} z0 {collision_meta['z0']}, "
        f"{(TERRAIN_GENERATED_DIR / 'collision.bin').stat().st_size} bytes"
    )
    if args.lidar_check:
        samples = dem.lidar_ground_samples(build.grid, dem.lidar_paths(), bounds)
        corridor, _ = trail.build_corridor(osm, curated.trail_spec())
        in_corridor = shapely.contains_xy(corridor, samples.x, samples.z)
        subsets = {
            "all in bbox": np.ones_like(in_corridor),
            f"slope <= {dem.GENTLE_SLOPE_DEGREES:.0f} deg": samples.slopes
            <= dem.GENTLE_SLOPE_DEGREES,
            "inside corridor": in_corridor,
        }
        print(f"lidar ground vs dem (noise dropped: {samples.noise})")
        for label, selected in subsets.items():
            stats = dem.error_stats(samples.errors[selected])
            print(
                f"  {label}: n={stats['count']:.0f} mean {stats['mean']:+.3f} m "
                f"rmse {stats['rmse']:.3f} m p95|e| {stats['p95Abs']:.3f} m "
                f"max|e| {stats['maxAbs']:.3f} m"
            )
    return 0


def _cmd_trail(args: argparse.Namespace) -> int:
    grid, meta = dem.load_dem(args.dem_dir)
    spec = tunnel.load_curated().trail_spec()
    document = trail.run_trail(
        grid, meta["source"], (TRAIL_GENERATED, TRAIL_BUILD), spec, artefacts.provenance("trail")
    )
    print(format_table(["GROUP", "OSM 2D", "2D", "3D", "ASCENT"], trail.report_rows(document)))
    print(f"anchors: {', '.join(document['anchors'])}")
    return 0


def _cmd_surfaces(args: argparse.Namespace) -> int:
    manifest = surfaces.run_surfaces(args.out_dir, artefacts.provenance("surfaces"))
    rows = [[name, f"{manifest['coverageM2'][name]:,.0f}"] for name in surfaces.CLASSES]
    print(format_table(["CLASS", "COVERAGE m2"], rows))
    sizes = sum(tile["bytes"] for tile in manifest["tiles"])
    print(
        f"surfaces: {len(manifest['tiles'])} tiles, {len(manifest['ways'])} ways, "
        f"{_megabytes(sizes)} of KTX2; skipped ways {manifest['skippedWays']}; "
        f"widths are {manifest['widths']['status']}"
    )
    return 0


def _cmd_structures(args: argparse.Namespace) -> int:
    report = structures.run_structures(
        args.out_dir, args.build_dir, artefacts.provenance("structures")
    )
    rows = [
        [
            s["id"],
            str(s["stepCount"]),
            f"{s['riser']:.3f}",
            f"{s['treadDepth']:.3f}",
            f"{s['mesh']['triangles']:,}",
        ]
        for s in report.document["staircases"]
    ]
    print(format_table(["STAIRCASE", "STEPS", "RISER m", "TREAD m", "TRIANGLES"], rows))
    print(
        f"structures.glb {report.glb_bytes} bytes, {report.triangles:,} triangles; "
        f"structures.json {report.json_bytes} bytes; constants are "
        f"{report.document['constants']['status']}"
    )
    return 0


def _cmd_buildings(args: argparse.Namespace) -> int:
    report = buildings.run_buildings(
        args.out_dir, args.build_dir, artefacts.provenance("buildings")
    )
    rows = [
        [
            b["id"],
            f"{b['eave']['y']:.2f}",
            f"{b['roof']['ridgeY']:.2f}",
            f"{b['roof']['fit']['rmse']:.2f}",
            str(len(b["turrets"])),
            f"{b['mesh']['triangles']:,}",
        ]
        for b in report.document["buildings"]
    ]
    print(
        format_table(["BUILDING", "EAVE y", "RIDGE y", "FIT RMSE m", "TURRETS", "TRIANGLES"], rows)
    )
    print(
        f"buildings.glb {report.glb_bytes} bytes, {report.triangles:,} triangles; "
        f"buildings.json {report.json_bytes} bytes; status {report.document['status']}"
    )
    return 0


def _megabytes(size: int) -> str:
    return f"{size / 1_000_000:.2f} MB"


def _cmd_terrain(args: argparse.Namespace) -> int:
    subset = args.tile is not None or args.no_far
    if subset and args.out_dir is None:
        print(
            "error: --tile and --no-far build a partial terrain; pass --out-dir so the app's "
            "manifest is not overwritten",
            file=sys.stderr,
        )
        return 2
    selected = [tiles.parse_tile_id(text) for text in args.tile] if args.tile else None
    report = tiles.run_terrain(
        out_dir=args.out_dir or TERRAIN_GENERATED_DIR,
        build_dir=args.build_dir,
        tiles=selected,
        include_far=not args.no_far,
        quality=args.texture_quality,
        features=tunnel.load_terrain_features(),
    )
    manifest = report.manifest
    rows: list[list[str]] = []
    for level in range(len(tiles.LODS)):
        lods = [t["lods"][level] for t in manifest["near"]["tiles"]]
        rows.append(
            [
                f"near LOD{level}",
                str(len(lods)),
                f"{sum(lod['triangles'] for lod in lods):,}",
                _megabytes(sum(lod["bytes"] for lod in lods)),
            ]
        )
    far = manifest.get("far")
    if far:
        rows.append(["far", "1", f"{far['triangles']:,}", _megabytes(far["bytes"])])
    print(format_table(["MESH", "FILES", "TRIANGLES", "BYTES"], rows))
    if not subset:
        start = tiles.start_area_bytes(manifest)
        verdict = "within" if start["total"] <= tiles.DOWNLOAD_BUDGET_BYTES else "OVER"
        print(
            f"start area download: far {_megabytes(start['far'])} "
            f"+ LOD2 {_megabytes(start['lod2'])} "
            f"+ LOD0/1 within {tiles.START_RADIUS:.0f} m {_megabytes(start['nearLod0Lod1'])} "
            f"= {_megabytes(start['total'])} ({verdict} the "
            f"{_megabytes(tiles.DOWNLOAD_BUDGET_BYTES)} budget)"
        )
    if report.corridor_margin is not None:
        print(f"trail corridor margin inside the near box: {report.corridor_margin:.1f} m")
    print(f"orthophoto pixels outside the image (filled with sea colour): {report.outside_pixels}")
    print(f"terrain built in {report.seconds:.1f} s")
    return 0


def _cmd_tunnel(args: argparse.Namespace) -> int:
    curated = tunnel.load_curated()
    if args.analyse:
        found = tunnel.analyse_data(curated)
        for name, portal, fresh in (
            ("west", curated.west, found.west),
            ("east", curated.east, found.east),
        ):
            print(
                f"{name} portal: curated floor {portal.value} m "
                f"(range {portal.low}-{portal.high} m, approximate)"
            )
            rows = [[key, f"{value:.2f}"] for key, value in fresh.items()]
            print(format_table(["EVIDENCE", "VALUE"], rows))
        drift = tunnel.evidence_drift(curated, found)
        for problem in drift:
            print(f"DRIFT {problem}")
        print(
            "evidence in data/curated/tunnel.toml " + ("DRIFTED" if drift else "matches the data")
        )
        return 1 if drift else 0
    report = tunnel.run_tunnel(
        out_dir=args.out_dir, build_dir=args.build_dir, with_tiles=not args.skip_tiles
    )
    width, height = report.document["width"], report.document["height"]
    print(
        f"tunnel (status {report.document['status']}): floor {curated.west.value} m -> "
        f"{curated.east.value} m, slope {report.slope_degrees:.1f} deg, section "
        f"{width} x {height} m"
    )
    print(f"tunnel.json {report.json_bytes} bytes, {len(report.document['axis'])} axis points")
    print(f"tunnel.glb {report.glb_bytes} bytes, {report.shell_triangles} triangles")
    if report.tiles:
        names = ", ".join(tiles.tile_id(i, j) for i, j in report.tiles)
        print(
            f"terrain tiles re-exported with the carved approach and portal openings: {names} "
            f"({report.tile_triangles:,} triangles, {_megabytes(report.tile_bytes)}; "
            f"openings in LOD {', '.join(map(str, tiles.OPENING_LODS))})"
        )
    return 0


def _cmd_vegetation(args: argparse.Namespace) -> int:
    if args.analyse:
        found = vegetation.detect(args.threshold)
        print(vegetation.analysis_report(found, args.threshold))
        return 0
    doc = vegetation.run_vegetation(args.out, args.threshold)
    counts, shrubs = doc["counts"], doc["understory"]
    print(
        f"crowns: {counts['crownsDetected']} detected, {counts['crownsTooTall']} too tall, "
        f"{counts['crownsAbsent']} absent in the 2024 orthophoto (NDVI < {args.threshold}), "
        f"{counts['crownsCliff']} cliff artefacts, {counts['crownsOverPath']} over the path, "
        f"{counts['crownsKept']} kept ({counts['crownsLeaning']} leaning off the corridor)"
    )
    print(
        f"pilot band (421 m + 40 m): {counts['pilotBandPark']} detected, "
        f"{counts['pilotBandKept']} kept"
    )
    print(f"understory: {shrubs['count']} instances")
    print(f"wrote {args.out} ({args.out.stat().st_size} bytes)")
    return 0


def _cmd_pine(args: argparse.Namespace) -> int:
    from penyal_pipeline.blender import pine

    document = pine.run_pine(args.out_dir, args.build_dir)
    rows = [[m["name"], str(m["triangles"]), str(m["vertices"])] for m in document["meshes"]]
    print(format_table(["MESH", "TRIANGLES", "VERTICES"], rows))
    print(f"{pine.PINE_GLB}: {document['file']['bytes']} bytes in {args.out_dir}")
    return 0


def _cmd_plants(args: argparse.Namespace) -> int:
    from penyal_pipeline.blender import plants

    document = plants.run_plants(args.out_dir, args.build_dir)
    rows = [[m["name"], str(m["triangles"]), str(m["vertices"])] for m in document["meshes"]]
    print(format_table(["MESH", "TRIANGLES", "VERTICES"], rows))
    print(f"{plants.PLANTS_GLB}: {document['file']['bytes']} bytes in {args.out_dir}")
    return 0


def _cmd_verify_generated(args: argparse.Namespace) -> int:
    problems = provenance.verify_generated(args.assets_dir)
    for problem in problems:
        print(f"FAIL {problem.artefact}: {problem.message}")
    if not problems:
        print(f"all {len(provenance.ARTEFACTS)} generated artefacts match their recorded inputs")
    return 1 if problems else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="penyal", description="Penyal d'Ifac 3D data pipeline")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    commands = parser.add_subparsers(dest="command", required=True)

    doctor_cmd = commands.add_parser("doctor", help="check the toolchain")
    doctor_cmd.add_argument("--json", action="store_true", help="machine-readable output")
    doctor_cmd.set_defaults(handler=_cmd_doctor)

    fetch_cmd = commands.add_parser("fetch", help="download catalogue sources")
    fetch_cmd.add_argument("--phase", type=int, required=True, help="catalogue phase to fetch")
    fetch_cmd.add_argument("--only", nargs="+", metavar="ID", help="restrict to these ids")
    mode = fetch_cmd.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="list what would be downloaded")
    mode.add_argument("--verify", action="store_true", help="check data/raw against the manifest")
    fetch_cmd.add_argument(
        "--refresh",
        action="store_true",
        help="re-download OSM and WFS snapshots already present (implies --update-lock for them)",
    )
    fetch_cmd.add_argument(
        "--update-lock",
        action="store_true",
        help="accept changed files or source definitions in manifest.lock.json",
    )
    fetch_cmd.add_argument(
        "--nat64-prefix",
        default=os.environ.get("PENYAL_NAT64_PREFIX"),
        metavar="PREFIX/96",
        help="reach IPv4-only hosts over an IPv6-only uplink through this NAT64 prefix "
        "(default: $PENYAL_NAT64_PREFIX)",
    )
    fetch_cmd.set_defaults(handler=_cmd_fetch)

    spike_cmd = commands.add_parser("spike", help="export the deterministic asset spike (GLB)")
    spike_cmd.add_argument("--out", type=Path, default=SPIKE_GLB, help="output .glb path")
    spike_cmd.set_defaults(handler=_cmd_spike)

    dem_cmd = commands.add_parser("dem", help="clip the MDT, fill the sea, write the heightfields")
    dem_cmd.add_argument(
        "--lidar-check", action="store_true", help="compare the LiDAR ground points with the DEM"
    )
    dem_cmd.set_defaults(handler=_cmd_dem)

    trail_cmd = commands.add_parser("trail", help="build trail.json (route, corridor, anchors)")
    trail_cmd.add_argument(
        "--dem-dir", type=Path, default=TERRAIN_BUILD_DIR, help="directory with dem.f32 / dem.json"
    )
    trail_cmd.set_defaults(handler=_cmd_trail)

    tunnel_cmd = commands.add_parser(
        "tunnel",
        help="build tunnel.json + tunnel.glb and re-export the terrain tiles the tunnel cuts",
    )
    tunnel_cmd.add_argument(
        "--out-dir",
        type=Path,
        default=GENERATED_DIR,
        help="where tunnel.json, tunnel.glb and terrain/ live (default: %(default)s)",
    )
    tunnel_cmd.add_argument(
        "--build-dir",
        type=Path,
        default=BUILD_DIR / "tunnel",
        help="where the unoptimised GLBs are written (default: %(default)s)",
    )
    tunnel_cmd.add_argument(
        "--skip-tiles", action="store_true", help="do not re-export the terrain tiles"
    )
    tunnel_cmd.add_argument(
        "--analyse",
        action="store_true",
        help="recompute the evidence in data/curated/tunnel.toml from the DEM and LiDAR; "
        "builds nothing, exits 1 if the file has drifted",
    )
    tunnel_cmd.set_defaults(handler=_cmd_tunnel)

    terrain_cmd = commands.add_parser(
        "terrain", help="build terrain tiles (RTIN + orthophoto), export and optimise GLBs"
    )
    terrain_cmd.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="output directory (default: app/public/assets/generated/terrain)",
    )
    terrain_cmd.add_argument(
        "--build-dir",
        type=Path,
        default=TERRAIN_BUILD_DIR / "glb",
        help="where the unoptimised GLBs are written (default: %(default)s)",
    )
    terrain_cmd.add_argument(
        "--tile",
        nargs="+",
        metavar="ID",
        help="build only these tiles (t_<i>_<j>); needs --out-dir",
    )
    terrain_cmd.add_argument("--no-far", action="store_true", help="skip far.glb; needs --out-dir")
    terrain_cmd.add_argument(
        "--texture-quality",
        type=int,
        default=tiles.TEXTURE_QUALITY,
        metavar="1-255",
        help="ETC1S quality passed to scripts/optimize.mjs (default: %(default)s)",
    )
    terrain_cmd.set_defaults(handler=_cmd_terrain)

    surfaces_cmd = commands.add_parser(
        "surfaces", help="rasterise the OSM path surfaces into per-tile class masks (KTX2)"
    )
    surfaces_cmd.add_argument(
        "--out-dir",
        type=Path,
        default=surfaces.SURFACES_GENERATED_DIR,
        help="output directory (default: %(default)s)",
    )
    surfaces_cmd.set_defaults(handler=_cmd_surfaces)

    structures_cmd = commands.add_parser(
        "structures", help="build the OSM staircases: structures.glb + structures.json"
    )
    structures_cmd.add_argument(
        "--out-dir",
        type=Path,
        default=GENERATED_DIR,
        help="where structures.glb and structures.json go (default: %(default)s)",
    )
    structures_cmd.add_argument(
        "--build-dir",
        type=Path,
        default=structures.STRUCTURES_BUILD_DIR,
        help="where the unoptimised GLB is written (default: %(default)s)",
    )
    structures_cmd.set_defaults(handler=_cmd_structures)

    buildings_cmd = commands.add_parser(
        "buildings", help="build the visitor-centre buildings: buildings.glb + buildings.json"
    )
    buildings_cmd.add_argument(
        "--out-dir",
        type=Path,
        default=GENERATED_DIR,
        help="where buildings.glb and buildings.json go (default: %(default)s)",
    )
    buildings_cmd.add_argument(
        "--build-dir",
        type=Path,
        default=buildings.BUILDINGS_BUILD_DIR,
        help="where the unoptimised GLB is written (default: %(default)s)",
    )
    buildings_cmd.set_defaults(handler=_cmd_buildings)
    pine_cmd = commands.add_parser(
        "pine", help="build the procedural Aleppo-pine GLB (variants, LODs, far card)"
    )
    pine_cmd.add_argument(
        "--out-dir", type=Path, default=PINE_GENERATED, help="pine.glb + pine.json (%(default)s)"
    )
    pine_cmd.add_argument(
        "--build-dir", type=Path, default=PINE_BUILD, help="unoptimised GLB (%(default)s)"
    )
    pine_cmd.set_defaults(handler=_cmd_pine)

    plants_cmd = commands.add_parser(
        "plants", help="build the procedural understory GLB (lentisc, rosemary, grass)"
    )
    plants_cmd.add_argument(
        "--out-dir",
        type=Path,
        default=PINE_GENERATED,
        help="plants.glb + plants.json (%(default)s)",
    )
    plants_cmd.add_argument(
        "--build-dir", type=Path, default=PLANTS_BUILD, help="unoptimised GLB (%(default)s)"
    )
    plants_cmd.set_defaults(handler=_cmd_plants)

    vegetation_cmd = commands.add_parser(
        "vegetation", help="build vegetation.json (LiDAR crowns, NDVI check, understory)"
    )
    vegetation_cmd.add_argument(
        "--out", type=Path, default=vegetation.VEGETATION_GENERATED, help="%(default)s"
    )
    vegetation_cmd.add_argument(
        "--threshold",
        type=float,
        default=vegetation.NDVI_ABSENT_THRESHOLD,
        help="NDVI below which a crown counts as gone (default: %(default)s)",
    )
    vegetation_cmd.add_argument(
        "--analyse",
        action="store_true",
        help="print counts and the NDVI histogram; writes nothing",
    )
    vegetation_cmd.set_defaults(handler=_cmd_vegetation)

    verify_cmd = commands.add_parser(
        "verify-generated",
        help="check that the inputs recorded in the generated artefacts still match the sources",
    )
    verify_cmd.add_argument(
        "--assets-dir",
        type=Path,
        default=GENERATED_DIR,
        help="generated assets directory (default: %(default)s)",
    )
    verify_cmd.set_defaults(handler=_cmd_verify_generated)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        return int(args.handler(args))
    except (
        CatalogError,
        fetch.FetchError,
        RawDataError,
        dem.DemError,
        trail.TrailError,
        tiles.TerrainError,
        ortho.OrthoError,
        tunnel.TunnelError,
        provenance.ProvenanceError,
        tunnel_geometry.GeometryError,
        surfaces.SurfacesError,
        structures.StructuresError,
        buildings.BuildingsError,
        vegetation.VegetationError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
