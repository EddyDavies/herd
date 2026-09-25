#!/usr/bin/env bash
# Install the herd CLI (editable, via uv) and link its two skills into ~/.claude/skills.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
uv tool install --editable "$here" --force
for s in herd-orchestrator herd-worker; do
  ln -sfn "$here/skills/$s" "$HOME/.claude/skills/$s"
done
echo "herd installed: $(command -v herd)"
