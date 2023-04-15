#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SLACKDUMP_BIN="${REPO_ROOT}/slackdump"

log() {
  printf '[slackdump2html] %s\n' "$1"
}

fail() {
  printf '[slackdump2html] ERROR: %s\n' "$1" >&2
  exit 1
}

load_env_if_present() {
  if [[ -f "${REPO_ROOT}/.env" ]]; then
    # shellcheck disable=SC1091
    source "${REPO_ROOT}/.env"
  fi
}

ensure_uv() {
  if ! command -v uv >/dev/null 2>&1; then
    fail "uv is required. Install from https://docs.astral.sh/uv/getting-started/installation/"
  fi
}

ensure_slackdump() {
  if [[ -x "${SLACKDUMP_BIN}" ]]; then
    return
  fi

  if command -v slackdump >/dev/null 2>&1; then
    SLACKDUMP_BIN="$(command -v slackdump)"
    return
  fi

  fail "slackdump binary not found. Run ./install-slackdump.sh or place slackdump at repo root."
}

check_auth_vars() {
  load_env_if_present
  if [[ -z "${SLACK_TOKEN:-}" ]]; then
    fail "SLACK_TOKEN is not set. Add it in .env (see .env.example)."
  fi
  if [[ -z "${SLACK_COOKIE:-}" && -n "${COOKIE:-}" ]]; then
    export SLACK_COOKIE="${COOKIE}"
  fi
  if [[ -z "${SLACK_COOKIE:-}" ]]; then
    fail "SLACK_COOKIE (or COOKIE) is not set. Add it in .env (see .env.example)."
  fi
}

ensure_workspace() {
  ensure_slackdump
  check_auth_vars

  local workspace_file
  workspace_file="${HOME}/.cache/slackdump/workspace.txt"
  if [[ -s "${workspace_file}" ]]; then
    return
  fi

  local cookie_source
  cookie_source="${COOKIE:-${SLACK_COOKIE:-}}"

  log "No slackdump workspace configured. Creating default workspace..."
  "${SLACKDUMP_BIN}" workspace new -token "${SLACK_TOKEN}" -cookie "${cookie_source}" default >/dev/null
}

slackdump_cmd() {
  ensure_slackdump
  printf '%s' "${SLACKDUMP_BIN}"
}
