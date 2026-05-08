#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$REPO_ROOT/remarkable.zip"

cd "$REPO_ROOT"

# Collect plugin files (everything except dev scaffolding)
EXCLUDES=(
    ".git"
    ".venv"
    ".claude"
    ".gitignore"
    ".pytest_cache"
    "__pycache__"
    "*.pyc"
    "tests"
    "scripts"
    "README.md"
    "LICENSE"
    "pytest.ini"
    "remarkable.zip"
    "*.egg-info"
)

rm -f "$OUT"

EXCLUDE_ARGS=()
for pat in "${EXCLUDES[@]}"; do
    EXCLUDE_ARGS+=(-x "*/${pat}/*" -x "*${pat}*")
done

zip -r "$OUT" . "${EXCLUDE_ARGS[@]}" -x "*.DS_Store"

echo "Built: $OUT"

if command -v calibre-customize &>/dev/null; then
    read -r -p "Install into Calibre now? [y/N] " ans
    if [[ "${ans,,}" == "y" ]]; then
        calibre-customize -a "$OUT"
        echo "Installed."
    fi
else
    echo "(calibre-customize not found — install manually via Preferences → Plugins → Load plugin from file)"
fi
