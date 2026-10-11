# 0003. Run Blender headless as the bpy module inside a uv-managed venv

- Status: accepted
- Date: 2026-10-11
- Deciders: tech lead

## Context
The brief requires Blender in headless mode with Python scripts as the asset pipeline. Blender is not installed on the development machine, global installs are not allowed, and the pipeline must be reproducible from a lockfile. PyPI publishes `bpy` 5.2.2 (Blender 5.2 LTS) with a `macosx_11_0_arm64` wheel; it requires Python 3.13 exactly. The geospatial steps need rasterio (bundled GDAL), laspy with the lazrs backend and pyproj, which also install from PyPI.

## Options considered
1. **`bpy` 5.2.2 in a uv venv (`pipeline/`)** — one lockfile pins Blender and the GIS stack, no app install, scripts call Blender's API in-process. Risk: the wheel might lack an add-on we need (glTF exporter). Cost to reverse: low (scripts are plain bpy).
2. **Blender.app 5.2 LTS portable in `tools/`, driven with `blender -b -P script.py`** — the official binary with every add-on, but not pinned by a lockfile and a second Python runtime to keep in sync.
3. **Docker image with Blender** — reproducible, but Linux arm64 images are not confirmed and file I/O through the container slows iteration.

## Decision
Option 1, verified by `penyal doctor`, which exports a test `.glb` from inside bpy. Option 2 remains the fallback if the wheel ever lacks something.

## Consequences
- The pipeline is pinned to Python 3.13 while bpy 5.2 requires it.
- Blender code lives in `pipeline/src/penyal_pipeline/blender/` and is typed loosely (no official stubs).
- Upgrading Blender is a `uv lock --upgrade-package bpy` plus a re-run of the asset determinism tests.
