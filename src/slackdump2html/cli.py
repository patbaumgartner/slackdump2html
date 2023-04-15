import sys
from pathlib import Path

from slackdump2html.HtmlPrinter import HtmlPrinter
from slackdump2html.SlackDataCleaner import SlackDataCleaner
from slackdump2html.SlackDumpReader import SlackDumpReader


def get_export_path_and_channel_id() -> list[str]:
    if len(sys.argv) != 3:
        raise ValueError("Please provide an export folder and a channel ID.")
    if not Path(sys.argv[1]).exists():
        raise ValueError("Please provide an existing export folder.")
    return [sys.argv[1], sys.argv[2]]


def main() -> None:
    export_path, channel_id = get_export_path_and_channel_id()
    input_file = f"{export_path}/{channel_id}.json"

    data_cleaner = SlackDataCleaner()

    print("Reading slack dump...", flush=True)
    reader = SlackDumpReader(data_cleaner)
    slack_data = reader.read(input_file)

    print("Cleaning data...", flush=True)
    data_cleaner.replace_names(slack_data)

    print("Printing output file...", flush=True)
    html_printer = HtmlPrinter(slack_data, channel_id)
    html_printer.print()
