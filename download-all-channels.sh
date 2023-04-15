#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/scripts/lib.sh"

ensure_workspace
cmd="$(slackdump_cmd)"

channels_file="${REPO_ROOT}/data/channels.txt"
mkdir -p "${REPO_ROOT}/data/messages"

if [[ ! -f "${channels_file}" ]]; then
  log "channels.txt not found. Exporting channels first..."
  "${cmd}" list channels -load-env -no-json >"${channels_file}"
fi

mapfile -t channel_ids < <(awk 'NR > 1 {print $1}' "${channels_file}" | grep -E '^[CGP][A-Z0-9]+$' || true)

if [[ ${#channel_ids[@]} -eq 0 ]]; then
  fail "No channel IDs found in ${channels_file}."
fi

limit="${SLACKDUMP2HTML_LIMIT:-0}"
channel_delay="${SLACKDUMP2HTML_CHANNEL_DELAY:-5}"
max_retries="${SLACKDUMP2HTML_MAX_RETRIES:-2}"
base_backoff="${SLACKDUMP2HTML_BACKOFF_SECONDS:-30}"
processed=0
downloaded=0
skipped=0
failed=0

if [[ ! "${channel_delay}" =~ ^[0-9]+$ ]]; then
  fail "SLACKDUMP2HTML_CHANNEL_DELAY must be a non-negative integer."
fi

if [[ ! "${max_retries}" =~ ^[0-9]+$ ]]; then
  fail "SLACKDUMP2HTML_MAX_RETRIES must be a non-negative integer."
fi

if [[ ! "${base_backoff}" =~ ^[0-9]+$ ]]; then
  fail "SLACKDUMP2HTML_BACKOFF_SECONDS must be a non-negative integer."
fi

for channel_id in "${channel_ids[@]}"; do
  if [[ "${limit}" =~ ^[0-9]+$ ]] && [[ "${limit}" -gt 0 ]] && [[ "${processed}" -ge "${limit}" ]]; then
    log "Reached SLACKDUMP2HTML_LIMIT=${limit}; stopping early."
    break
  fi

  ((processed += 1))
  target_file="${REPO_ROOT}/data/messages/${channel_id}.json"

  if [[ -f "${target_file}" ]]; then
    ((skipped += 1))
    log "[${processed}] ${channel_id}: skip (already downloaded)"
    continue
  fi

  log "[${processed}] ${channel_id}: downloading"
  attempt=0
  channel_ok=0
  while [[ "${attempt}" -le "${max_retries}" ]]; do
    ((attempt += 1))
    tmp_root="$(mktemp -d)"
    tmp_out="${tmp_root}/export"

    if "${cmd}" dump -load-env -o "${tmp_out}" "${channel_id}"; then
      source_file="$(find "${tmp_out}" -type f -name "${channel_id}.json" | head -n 1)"
      if [[ -z "${source_file}" ]]; then
        source_file="$(find "${tmp_out}" -type f -name '*.json' | head -n 1)"
      fi

      if [[ -n "${source_file}" ]]; then
        cp "${source_file}" "${target_file}"
        ((downloaded += 1))
        channel_ok=1
      else
        log "[${processed}] ${channel_id}: dump succeeded but no JSON file was found"
      fi
    else
      log "[${processed}] ${channel_id}: attempt ${attempt}/$((max_retries + 1)) failed"
    fi

    rm -rf "${tmp_root}"

    if [[ "${channel_ok}" -eq 1 ]]; then
      break
    fi

    if [[ "${attempt}" -le "${max_retries}" ]]; then
      sleep_seconds=$((base_backoff * attempt))
      if [[ "${sleep_seconds}" -gt 0 ]]; then
        log "[${processed}] ${channel_id}: retrying in ${sleep_seconds}s"
        sleep "${sleep_seconds}"
      fi
    fi
  done

  if [[ "${channel_ok}" -eq 0 ]]; then
    ((failed += 1))
    log "[${processed}] ${channel_id}: failed after $((max_retries + 1)) attempts"
  fi

  if [[ "${channel_delay}" -gt 0 ]]; then
    sleep "${channel_delay}"
  fi
done

log "Download summary: processed=${processed}, downloaded=${downloaded}, skipped=${skipped}, failed=${failed}"
log "Run ./audit-export-features.sh to inspect missing rendering features in downloaded data."
