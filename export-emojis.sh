#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/scripts/lib.sh"

ensure_workspace
cmd="$(slackdump_cmd)"

rm -rf "${REPO_ROOT}/data/emojis"

log "Exporting emojis to data/emojis"
"${cmd}" emoji -load-env -o "${REPO_ROOT}/data/emojis"
log "Done"
