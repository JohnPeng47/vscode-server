#!/usr/bin/env bash
# Clone all repos needed by diagfren into data/repos/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPOS_DIR="$SCRIPT_DIR/data/repos"

mkdir -p "$REPOS_DIR"

clone_if_missing() {
  local name="$1"
  local url="$2"
  local dest="$REPOS_DIR/$name"

  if [ -d "$dest" ]; then
    echo "  $name: already exists, skipping"
  else
    echo "  $name: cloning from $url"
    git clone "$url" "$dest"
  fi
}

echo "Installing repos..."
clone_if_missing "kanban" "/home/john/kanban"

echo ""
echo "Done. Repos installed to $REPOS_DIR"
