# Slackdump2Html

[![CI](https://github.com/patbaumgartner/slackdump2html/actions/workflows/ci.yml/badge.svg)](https://github.com/patbaumgartner/slackdump2html/actions/workflows/ci.yml)
[![CodeQL](https://github.com/patbaumgartner/slackdump2html/actions/workflows/codeql.yml/badge.svg)](https://github.com/patbaumgartner/slackdump2html/actions/workflows/codeql.yml)
[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE.md)
[![Release](https://img.shields.io/github/v/release/patbaumgartner/slackdump2html)](https://github.com/patbaumgartner/slackdump2html/releases)

This script transforms a JSON file created by [slackdump](https://github.com/rusq/slackdump) to a static HTML file.

A lot of companies that switch from Slack to another communication tool lose a lot of implicit knowledge that has been gathered potentially over years.

To preserve this knowledge in a human-readable and easily searchable way, we have created this script.
The output file is a self-contained HTML document that can easily be uploaded to any web or file server or shared with specific people in your organization.

The converter supports core message text, threads, reactions, mentions, images, and common file cards/previews.

## Why this project

Slack workspaces often contain critical historical decisions and context. This tool converts `slackdump` exports into a standalone, searchable HTML archive that can be hosted or shared with minimal effort.

## Quickstart

```bash
uv sync --all-groups
uv run slackdump2html data/messages C03HQM5DE
```

Output will be written to `out/<channel-name>.html`.

## Setup

### Slackdump

Before converting JSON dumps, install and configure `slackdump`.

Automatic install:

```bash
./install-slackdump.sh
```

The script installs `slackdump` to the repository root.

Follow the [slackdump User Guide](https://github.com/rusq/slackdump/blob/master/doc/README.rst) to install and set up the tool and provide your authentication tokens.

Create an auth file from the template:

```bash
cp .env.example .env
```

Edit `.env` and set:

- `SLACK_TOKEN` (for example `xoxc-...`)
- `COOKIE` path (for example `./app.slack.com_cookies.txt`)

To get your channel ids, use this command:

```bash
./export-channels.sh
-- or
./slackdump -list-channels > data/channels.txt
```

You'll also need a user dump:

```bash
./export-users.sh
-- or
./slackdump -list-users > data/users.txt
```

You'll also need an emoji dump:

```bash
./export-emojis.sh
-- or
./slackdump -emoji -base data/emojis
```

### Python

This project now uses [uv](https://github.com/astral-sh/uv) for environment, dependency, and command management.

Install uv and sync the project:

```bash
uv sync --all-groups
```

Run the CLI with uv:

```bash
uv run slackdump2html <path-to-your-export-files> <your-channel-id>
```

Install the package in editable mode (if needed):

```bash
uv pip install -e .
```

Development commands:

```bash
uv run ruff check .
uv run ruff format .
uv run mypy
uv run pytest
uv run bandit -c pyproject.toml -r src
uv run pip-audit
```

Optional: install local hooks so checks run before commit.

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

## Usage

### Automatically

Fetch the ID of the channel (e.g. `C03HQM5DE`) you want to export from the `data/channels.txt` file and run the following command.

```bash
./dump-and-convert.sh
```

Provide the channel ID when it asks for it. You'll find your output file in `out/<channel-name>.html`.

The script validates auth and tooling first, then downloads and converts in one run.

Behavior details:

- If prerequisite data files are missing, the script auto-runs the corresponding exporters:
  - missing `data/users.txt` and `data/users.json` -> `./export-users.sh`
  - missing `data/emojis/index.json` -> `./export-emojis.sh`
  - missing `data/channels.txt` -> `./export-channels.sh`
- Channel download uses a temporary output path and copies the resulting JSON into `data/messages/<channel-id>.json`, which avoids the `slackdump` overwrite prompt for existing `data/messages` folders.

### Whole workspace audit workflow

Download all channels and then generate a feature-gap report:

```bash
./download-all-channels.sh
./audit-export-features.sh
```

The audit report is written to `out/feature-audit.md` and highlights high-frequency Slack features that are not fully rendered yet.

Optional: limit the number of channels during a trial run.

```bash
SLACKDUMP2HTML_LIMIT=10 ./download-all-channels.sh
```

Optional: tune rate-limit resilience for large workspaces.

```bash
SLACKDUMP2HTML_CHANNEL_DELAY=10 \
SLACKDUMP2HTML_MAX_RETRIES=4 \
SLACKDUMP2HTML_BACKOFF_SECONDS=45 \
./download-all-channels.sh
```

### Manually

You'll need to dump the channel you want to convert via `slackdump`.
Use the `data/channels.txt` file to get the ID of your channel (e.g. `C03HQM5DE`) and use `slackdump` to dump the channel to a JSON file.
Grab a coffee, this might take a while.

```bash
./slackdump -download -base data/messages <your-channel-id>
-- or
./slackdump -download -base data/messages C03HQM5DE
```

Convert your `slackdump` to an HTML file with this command.

```bash
slackdump2html <path-to-your-export-files> <your-channel-id>
-- or
slackdump2html data/messages C03HQM5DE
```

You'll find your output file in `out/<channel-name>.html`.

## Known issues

* Emojis:
  * The Python `emoji` package does not consider markup languages and replaces emojis in HTML links. This might break some of your links.
  * Not all emojis can be replaced correctly.
  * Not all image types are supported as custom emojis.

* File attachments:
  * Basic file cards are supported.
  * Inline previews currently focus on images, video (`video/*`), and PDF (`application/pdf`).
  * Some file types still render as links/cards only.

* Code blocks:
  * Some formatting in code blocks is broken.

* EZ-Login 3000 in `slackdump` might not work in Linux/WSL:
  * Define a `.env` file with a `SLACK_TOKEN=xoxc-...` and `COOKIE=./app.slack.com_cookies.txt` variable.
  * Or pass the via command line arguments `-t xoxc-... -cookie ./app.slack.com_cookies.txt`

## Contributing

Contributions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

For vulnerabilities, use private reporting as documented in [SECURITY.md](SECURITY.md).

## Releases

This project uses GitHub releases and automated package publishing.

- Changelog: [CHANGELOG.md](CHANGELOG.md)
- Roadmap: [ROADMAP.md](ROADMAP.md)

## Code of Conduct

Participation in this project is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
