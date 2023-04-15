#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/scripts/lib.sh"

ensure_uv

report_path="${1:-${REPO_ROOT}/out/feature-audit.md}"

mkdir -p "${REPO_ROOT}/out"

log "Auditing Slack export features from ${REPO_ROOT}/data/messages"
uv run python "${REPO_ROOT}/scripts/audit_export_features.py" \
  --export-dir "${REPO_ROOT}/data/messages" \
  --report "${report_path}"

log "Feature audit completed: ${report_path}"
