# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- uv-based modern Python packaging and development workflow.
- Matrix CI, CodeQL, dependency audit, and release publishing workflows.
- Governance and contributor community standards documentation.
- `--help` and `--version` command line flags, and error messages that report
  usage problems on stderr with exit code 2 and runtime problems with exit
  code 1 instead of printing a Python traceback.
- Packaging smoke test in CI: build the wheel, install it into a clean
  environment, and convert a fixture dump with the installed CLI.

### Changed

- Refactored internals for safer file handling and improved testability.
- Increased test coverage and enforced a 90% minimum threshold.
- CI tests Python 3.13 and 3.14 on Linux, macOS, and Windows instead of 3.13
  only, and syncs dependencies with `uv sync --all-groups --locked`.
- The pre-commit mypy hook now uses the same mypy version as `uv.lock`.

### Fixed

- All dump-derived content is HTML-escaped before it reaches the published
  file: message text, channel heading, `<title>`, reaction names, custom
  emoji CSS classes, and output file names. Any workspace member can post
  the exported content, so this closes a stored cross-site scripting risk
  in published archives.
- Message formatting no longer leaks into fenced code blocks or into the
  label of a link, and emoji aliases in link labels render again without
  altering the link target.
- Reader-generated markup (shared images, file cards, attachments) is kept
  out of the message formatter, so it stays intact while message text is
  escaped.
- Messages with a missing or blank author no longer abort the conversion.
- `install-slackdump.sh` verifies the downloaded archive against the
  publisher's `checksums.txt` SHA-256 sums, and resolves the macOS assets
  (`slackdump_macOS_*`), which previously failed with HTTP 404 on every
  macOS machine.

### Removed

- Legacy Pipenv and setup.py packaging files.
