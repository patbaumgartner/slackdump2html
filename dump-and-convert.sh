#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/scripts/lib.sh"

ensure_workspace
ensure_uv
cmd="$(slackdump_cmd)"

if [[ ! -f "${REPO_ROOT}/data/users.txt" && ! -f "${REPO_ROOT}/data/users.json" ]]; then
	log "users data not found. Exporting users first..."
	"${REPO_ROOT}/export-users.sh"
fi

if [[ ! -f "${REPO_ROOT}/data/emojis/index.json" ]]; then
	log "emoji data not found. Exporting emojis first..."
	"${REPO_ROOT}/export-emojis.sh"
fi

if [[ ! -f "${REPO_ROOT}/data/channels.txt" ]]; then
	log "channels data not found. Exporting channels first..."
	"${REPO_ROOT}/export-channels.sh"
fi

echo "What channel should be exported?"
echo "Please enter the internal channel ID of Slack (for example C2R198BRC)"
read -r channel

if [[ -z "${channel}" ]]; then
	fail "Channel ID must not be empty."
fi

mkdir -p "${REPO_ROOT}/data/messages"

log "Downloading channel ${channel}"
tmp_root="$(mktemp -d)"
tmp_out="${tmp_root}/export"
trap 'rm -rf "${tmp_root}"' EXIT

"${cmd}" dump -load-env -o "${tmp_out}" "${channel}"

source_file="$(find "${tmp_out}" -type f -name "${channel}.json" | head -n 1)"
if [[ -z "${source_file}" ]]; then
	source_file="$(find "${tmp_out}" -type f -name '*.json' | head -n 1)"
fi

if [[ -z "${source_file}" ]]; then
	fail "Channel dump completed, but no JSON export file was found."
fi

cp "${source_file}" "${REPO_ROOT}/data/messages/${channel}.json"

log "Converting export to HTML"
uv run slackdump2html "${REPO_ROOT}/data/messages" "${channel}"

trap - EXIT
rm -rf "${tmp_root}"

log "Finished"
