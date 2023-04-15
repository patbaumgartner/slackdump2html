#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/scripts/lib.sh"

ensure_workspace
cmd="$(slackdump_cmd)"

mkdir -p "${REPO_ROOT}/data"
tmp_file="$(mktemp)"
tmp_json="$(mktemp)"
trap 'rm -f "${tmp_file}"' EXIT
trap 'rm -f "${tmp_file}" "${tmp_json}"' EXIT

log "Exporting users to data/users.txt"
"${cmd}" list users -load-env -format JSON -no-json > "${tmp_json}"
mv "${tmp_json}" "${REPO_ROOT}/data/users.json"

"${cmd}" list users -load-env -no-json > "${tmp_file}"
mv "${tmp_file}" "${REPO_ROOT}/data/users.txt"
trap - EXIT
log "Done"
