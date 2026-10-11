# Local tools

Binaries the pipeline needs that are not on PyPI or npm. They live here, not in the system, and are not committed (`tools/bin/`, `tools/ktx-*/` are gitignored). `uv run --project pipeline penyal doctor` reports whether they are present.

## KTX-Software 4.4.2 (`ktx`)
Used by `@gltf-transform/cli` (`etc1s`, `uastc`) to write KTX2 / Basis Universal textures.

1. Download the signed macOS package (6,785,364 bytes):
   `https://github.com/KhronosGroup/KTX-Software/releases/download/v4.4.2/KTX-Software-4.4.2-Darwin-arm64.pkg`
2. Install it into `tools/` (verifies sha256 `500bd8f9…032c3c` and the "Developer ID Installer: The Khronos Group, Inc. (TD2656HYNK)" signature, then expands it without running the installer):
   `tools/install-ktx.sh <path to the .pkg>`

The result is `tools/ktx-4.4.2/{bin,lib}` plus a `tools/bin/ktx` wrapper. Nothing is written outside the repository.

## IPv6-only networks
If the machine only has IPv6 (e.g. some phone hotspots), GitHub and the ICV servers are unreachable directly. Downloads can go through a NAT64 prefix: `PENYAL_NAT64_PREFIX=<prefix>/96 uv run --project pipeline penyal fetch …`. TLS is end-to-end, so certificates are still checked against the real host names.
