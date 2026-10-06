import json
import sys
from importlib import metadata
from pathlib import Path
from typing import NoReturn

from slackdump2html.HtmlPrinter import HtmlPrinter
from slackdump2html.SlackDataCleaner import SlackDataCleaner
from slackdump2html.SlackDumpReader import SlackDumpReader

USAGE = "usage: slackdump2html <export-folder> <channel-id>"
DESCRIPTION = (
    "Converts one channel of a slackdump export "
    "(<export-folder>/<channel-id>.json) into a self-contained HTML file "
    "written to out/<channel-name>.html."
)


def get_export_path_and_channel_id() -> list[str]:
    if len(sys.argv) != 3:
        raise ValueError("Please provide an export folder and a channel ID.")
    if not Path(sys.argv[1]).exists():
        raise ValueError("Please provide an existing export folder.")
    return [sys.argv[1], sys.argv[2]]


def _package_version() -> str:
    try:
        return metadata.version("slackdump2html")
    except metadata.PackageNotFoundError:
        return "unknown"


def _usage_error(error: str) -> NoReturn:
    """Report a usage problem on stderr and exit 2 (no traceback)."""
    if any(arg in ("-h", "--help") for arg in sys.argv[1:]):
        print("slackdump2html - convert a slackdump channel export to HTML")
        print(DESCRIPTION)
        print(USAGE)
        sys.exit(0)
    if any(arg in ("-V", "--version") for arg in sys.argv[1:]):
        print(f"slackdump2html {_package_version()}")
        sys.exit(0)
    print(f"error: {error}", file=sys.stderr)
    print(USAGE, file=sys.stderr)
    print("Run 'slackdump2html --help' for a description.", file=sys.stderr)
    sys.exit(2)


def _fail(error: str) -> NoReturn:
    """Report a runtime problem on stderr and exit 1 (no traceback)."""
    print(f"error: {error}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    try:
        export_path, channel_id = get_export_path_and_channel_id()
    except ValueError as error:
        _usage_error(str(error))

    input_file = f"{export_path}/{channel_id}.json"

    data_cleaner = SlackDataCleaner()

    print("Reading slack dump...", flush=True)
    reader = SlackDumpReader(data_cleaner)
    try:
        slack_data = reader.read(input_file)
    except FileNotFoundError:
        _fail(f"export file not found: {input_file}")
    except json.JSONDecodeError as error:
        _fail(f"{input_file} is not valid JSON: {error}")
    except UnicodeDecodeError:
        _fail(f"{input_file} is not UTF-8 encoded text")
    except OSError as error:
        _fail(f"could not read {input_file}: {error.strerror or error}")
    except (KeyError, TypeError) as error:
        _fail(f"{input_file} does not look like a slackdump export (problem: {error})")

    print("Cleaning data...", flush=True)
    data_cleaner.replace_names(slack_data)

    print("Printing output file...", flush=True)
    html_printer = HtmlPrinter(slack_data, channel_id)
    html_printer.print()
