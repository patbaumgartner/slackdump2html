#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/scripts/lib.sh"

TARGET_BIN="${REPO_ROOT}/slackdump"

if [[ -x "${TARGET_BIN}" ]]; then
    log "slackdump already exists at ${TARGET_BIN}"
    exit 0
fi

if ! command -v curl >/dev/null 2>&1; then
    fail "curl is required to download slackdump."
fi
if ! command -v tar >/dev/null 2>&1; then
    fail "tar is required to extract slackdump."
fi

os="$(uname -s)"
arch="$(uname -m)"

case "${os}" in
    Linux) platform_os="Linux" ;;
    Darwin) platform_os="Darwin" ;;
    *)
        fail "Unsupported OS: ${os}"
        ;;
esac

case "${arch}" in
    x86_64|amd64) platform_arch="x86_64" ;;
    arm64|aarch64) platform_arch="arm64" ;;
    *)
        fail "Unsupported architecture: ${arch}"
        ;;
esac

asset="slackdump_${platform_os}_${platform_arch}.tar.gz"
url="https://github.com/rusq/slackdump/releases/latest/download/${asset}"
tmp_dir="$(mktemp -d)"
archive_path="${tmp_dir}/${asset}"

cleanup() {
    rm -rf "${tmp_dir}"
}
trap cleanup EXIT

log "Downloading ${url}"
if ! curl -fsSL "${url}" -o "${archive_path}"; then
    fail "Automatic download failed for ${asset}. Install manually from https://github.com/rusq/slackdump/releases and place binary at ${TARGET_BIN}"
fi

tar -xzf "${archive_path}" -C "${tmp_dir}"
found_bin="$(find "${tmp_dir}" -type f -name 'slackdump' | head -n 1)"

if [[ -z "${found_bin}" ]]; then
    fail "Could not find slackdump binary in archive."
fi

cp "${found_bin}" "${TARGET_BIN}"
chmod +x "${TARGET_BIN}"

log "Installed slackdump to ${TARGET_BIN}"
"${TARGET_BIN}" -h | head -n 1 || true
