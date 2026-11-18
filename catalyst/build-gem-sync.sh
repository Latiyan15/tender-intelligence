#!/usr/bin/env bash
# Assemble the deployable Catalyst gem_sync function from authoritative sources.
#
# Authoritative, hand-written files live in catalyst/functions/gem_sync/
# (main.py, requirements.txt). The rest of the pipeline (gem_sheets_sync.py and
# the src/ package) stays single-sourced at the repo root and is vendored in
# here at build time. The deployable is assembled into functions/gem_sync/ —
# the folder `catalyst functions:add` scaffolds — leaving its CLI-generated
# catalyst-config.json untouched.
#
# Usage (from repo root, after `catalyst functions:add --name gem_sync ...`):
#   bash catalyst/build-gem-sync.sh
#   catalyst deploy --only functions:gem_sync
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/catalyst/functions/gem_sync"        # authoritative hand-written files
DEST="${1:-$ROOT/functions/gem_sync}"          # CLI scaffold location (deployable)

echo "Assembling deployable into $DEST ..."
mkdir -p "$DEST"

# Hand-written function files.
cp "$SRC/main.py"          "$DEST/main.py"
cp "$SRC/requirements.txt" "$DEST/requirements.txt"

# Orchestration module (single-sourced at repo root).
cp "$ROOT/gem_sheets_sync.py" "$DEST/gem_sheets_sync.py"

# Only the src/ modules the daily pipeline imports.
rm -rf "$DEST/src"
mkdir -p "$DEST/src/adapters" "$DEST/src/classifier" "$DEST/src/services" "$DEST/src/models" "$DEST/src/utils"
cp "$ROOT/src/adapters/base.py"               "$DEST/src/adapters/base.py"
cp "$ROOT/src/adapters/gem.py"                "$DEST/src/adapters/gem.py"
cp "$ROOT/src/classifier/gem_classifier.py"   "$DEST/src/classifier/gem_classifier.py"
cp "$ROOT/src/classifier/cyber_classifier.py" "$DEST/src/classifier/cyber_classifier.py"
cp "$ROOT/src/services/sheets_service.py"     "$DEST/src/services/sheets_service.py"
cp "$ROOT/src/models/tender.py"               "$DEST/src/models/tender.py"
cp "$ROOT/src/utils/http_client.py"           "$DEST/src/utils/http_client.py"

# EMPTY package markers — the real src/__init__.py files import sibling modules
# we deliberately don't vendor. Code imports submodules directly, so empty
# markers suffice (e.g. `from src.adapters.gem import GemAdapter`).
for d in src src/adapters src/classifier src/services src/models src/utils; do
  : > "$DEST/$d/__init__.py"
done

echo "Done. Next: catalyst deploy --only functions:gem_sync"
