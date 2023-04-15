#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/scripts/lib.sh"

ensure_workspace
cmd="$(slackdump_cmd)"

mkdir -p "${REPO_ROOT}/data"
rm -f "${REPO_ROOT}/data/channels.txt"

log "Exporting channels to data/channels.txt"
"${cmd}" list channels -load-env -no-json > "${REPO_ROOT}/data/channels.txt"
log "Done"
