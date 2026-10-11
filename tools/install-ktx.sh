#!/bin/bash
# Install KTX-Software (the `ktx` CLI used by gltf-transform for KTX2 textures) into tools/,
# without a system install. Verifies the package checksum and the Khronos Developer ID signature.
#
# Usage: tools/install-ktx.sh <path to KTX-Software-4.4.2-Darwin-arm64.pkg>
# Download from:
#   https://github.com/KhronosGroup/KTX-Software/releases/download/v4.4.2/KTX-Software-4.4.2-Darwin-arm64.pkg
set -euo pipefail

VERSION="4.4.2"
SHA256="500bd8f9d63358c3f3a0d83b724c8574436a72c37dc0e4bad90ec1ca38032c3c"
SIGNER="Developer ID Installer: The Khronos Group, Inc. (TD2656HYNK)"

pkg="${1:?usage: tools/install-ktx.sh <KTX-Software-${VERSION}-Darwin-arm64.pkg>}"
tools_dir="$(cd "$(dirname "$0")" && pwd)"
dest="$tools_dir/ktx-$VERSION"

actual="$(shasum -a 256 "$pkg" | cut -d' ' -f1)"
if [ "$actual" != "$SHA256" ]; then
  echo "error: $pkg has sha256 $actual, expected $SHA256 (KTX-Software $VERSION). Re-download it." >&2
  exit 1
fi
if ! pkgutil --check-signature "$pkg" | grep -qF "$SIGNER"; then
  echo "error: $pkg is not signed by '$SIGNER'. Do not use it." >&2
  exit 1
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
pkgutil --expand-full "$pkg" "$work/expanded"

rm -rf "$dest"
mkdir -p "$dest/bin" "$dest/lib" "$tools_dir/bin"
cp -a "$work/expanded/KTX-Software-$VERSION-Darwin-arm64-tools.pkg/Payload/usr/local/bin/ktx" "$dest/bin/"
cp -a "$work/expanded/KTX-Software-$VERSION-Darwin-arm64-library.pkg/Payload/usr/local/lib/"libktx.4*.dylib "$dest/lib/"

# The binary finds libktx through @executable_path/../lib, so it runs unmodified from $dest.
# The wrapper is relative so that the repository can be moved or cloned elsewhere.
cat > "$tools_dir/bin/ktx" <<EOF
#!/bin/bash
exec "\$(dirname "\$0")/../ktx-$VERSION/bin/ktx" "\$@"
EOF
chmod +x "$tools_dir/bin/ktx"

"$tools_dir/bin/ktx" --version
