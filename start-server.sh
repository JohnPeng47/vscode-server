#!/usr/bin/env bash
# Start code-server with diagfren extension pre-installed
# Opens a web-based VS Code IDE at http://localhost:8080

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="$HOME/.local/bin:$PATH"

# Build the extension first
echo "Building diagfren extension..."
cd "$SCRIPT_DIR"
npm run build

# Package the .vsix
echo "Packaging extension..."
npm run package

# Install/update the extension in code-server
VSIX=$(ls -t "$SCRIPT_DIR/dist/"*.vsix 2>/dev/null | head -1)
if [ -n "$VSIX" ]; then
  echo "Installing extension: $VSIX"
  code-server --install-extension "$VSIX" --force
else
  echo "ERROR: No .vsix found in dist/. Build may have failed."
  exit 1
fi

# Start code-server, opening the test-workspace by default
echo ""
echo "Starting code-server..."
echo "  URL:  http://localhost:8080"
echo "  Auth: none (no password required)"
echo ""
exec code-server --bind-addr 0.0.0.0:8080 --auth none "$SCRIPT_DIR/data.code-workspace"
