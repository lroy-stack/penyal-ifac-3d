"""Repository locations shared by the pipeline commands."""

from pathlib import Path

# src/penyal_pipeline/paths.py -> repository root is four levels up.
REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"
BUILD_DIR = REPO_ROOT / "build"
SPIKE_GLB = BUILD_DIR / "spike" / "spike.glb"
GENERATED_DIR = REPO_ROOT / "app" / "public" / "assets" / "generated"
TERRAIN_BUILD_DIR = BUILD_DIR / "terrain"
TERRAIN_GENERATED_DIR = GENERATED_DIR / "terrain"
TRAIL_BUILD = BUILD_DIR / "trail.json"
TRAIL_GENERATED = GENERATED_DIR / "trail.json"
CURATED_DIR = DATA_DIR / "curated"
TUNNEL_CURATED = CURATED_DIR / "tunnel.toml"
TUNNEL_BUILD_DIR = BUILD_DIR / "tunnel"
TUNNEL_JSON = "tunnel.json"
TUNNEL_GLB = "tunnel.glb"
PINE_GENERATED = GENERATED_DIR / "vegetation"
PINE_BUILD = BUILD_DIR / "pine"
