# data

Source data for the terrain pipeline.

| Path | Committed | What |
|---|---|---|
| `catalog.toml` | yes | Every external source: id, phase, URL, licence, attribution, expected size. |
| `manifest.lock.json` | yes | What was actually downloaded: per id the files (name, bytes, sha256), retrieval date, licence, attribution. |
| `curated/tunnel.toml` | yes | Hand-curated, approximate tunnel data (portal floor heights, cross-section) with method, evidence numbers and sources. Read by `penyal trail`, `penyal tunnel`, `penyal dem` and `penyal terrain`. |
| `raw/<id>/` | **no** (git-ignored) | The downloaded files. Large (about 1 GB for phase 1); recreated by `penyal fetch`. |

## Fetching

Run from the repository root:

```sh
uv run --project pipeline penyal fetch --phase 1 --dry-run   # list files, hosts, sizes, licences; downloads nothing
uv run --project pipeline penyal fetch --phase 1             # download (resumable; re-run after a network failure)
uv run --project pipeline penyal fetch --phase 1 --verify    # re-hash data/raw against manifest.lock.json
uv run --project pipeline penyal fetch --phase 1 --only osm-penyal icv-cv05-penyal
```

- Downloads stream to `<file>.part`, resume with HTTP `Range`, and are renamed atomically when complete.
- If a file's size differs from `expected_bytes` by more than its `size_tolerance` (default 1 %), the fetch fails and says so. The sizes in the catalogue are rounded values from HTTP `Content-Length` (2026-10-10), so after the first download replace them with exact values.
- An unconfirmed WFS layer (`confirmed = false`) that the server rejects is skipped with a warning.
- `manifest.lock.json` is rewritten after every source, with sorted keys and a trailing newline.

## Curated tunnel data

`curated/tunnel.toml` is not downloaded: it records the tunnel's floor heights and cross-section, which no source publishes, as approximations with their method and evidence (spec Q2, Q6).

```sh
uv run --project pipeline penyal tunnel --analyse   # recompute the evidence from the DEM and LiDAR; exit 1 if the file drifted
uv run --project pipeline penyal tunnel             # tunnel.json + tunnel.glb, and re-export the terrain tile(s) the tunnel cuts
```

Run `penyal dem`, `penyal trail` and `penyal tunnel` (in this order) after changing the file; `penyal terrain` applies the same carve and openings to a full rebuild.

## Licences

All ICV data (DTM, orthophoto, LiDAR, CV05) is CC BY 4.0: keep the `attribution` string of the catalogue entry in the app credits.
OpenStreetMap data is ODbL 1.0 (share-alike): it is stored as its own file (`raw/osm-penyal/osm-penyal.json`) and must not be merged into other datasets without checking the licence.
`miteco-ecocartografia-alicante-batimetria` has an unknown licence and is `optional`: ask before using it.
