import runpy
import sys
from pathlib import Path

import pytest

import slackdump2html.command_line as command_line
from slackdump2html import cli


class _FakeCleaner:
    def __init__(self):
        self.replace_names_called = False

    def replace_names(self, _slack_data):
        self.replace_names_called = True


class _FakeReader:
    def __init__(self, cleaner):
        self.cleaner = cleaner
        self.read_arg = None

    def read(self, path):
        self.read_arg = path
        return {"ok": True}


class _FakePrinter:
    def __init__(self, slack_data, channel_id):
        self.slack_data = slack_data
        self.channel_id = channel_id
        self.print_called = False

    def print(self):
        self.print_called = True


def test_get_export_path_and_channel_id_valid(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path), "C123"])
    assert cli.get_export_path_and_channel_id() == [str(tmp_path), "C123"]


def test_get_export_path_and_channel_id_invalid_argv(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    with pytest.raises(ValueError):
        cli.get_export_path_and_channel_id()


def test_get_export_path_and_channel_id_missing_path(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "missing-dir", "C123"])
    with pytest.raises(ValueError):
        cli.get_export_path_and_channel_id()


def test_cli_main_wires_reader_cleaner_printer(monkeypatch, tmp_path: Path):
    fake_cleaner = _FakeCleaner()
    fake_reader = _FakeReader(fake_cleaner)
    fake_printer = _FakePrinter({"ok": True}, "C2R198BRC")

    monkeypatch.setattr(cli, "SlackDataCleaner", lambda: fake_cleaner)
    monkeypatch.setattr(cli, "SlackDumpReader", lambda cleaner: fake_reader)
    monkeypatch.setattr(cli, "HtmlPrinter", lambda data, cid: fake_printer)
    monkeypatch.setattr(
        cli,
        "get_export_path_and_channel_id",
        lambda: [str(tmp_path), "C2R198BRC"],
    )

    cli.main()

    assert fake_reader.read_arg == f"{tmp_path}/C2R198BRC.json"
    assert fake_cleaner.replace_names_called is True
    assert fake_printer.print_called is True


def test_command_line_exports_cli_symbols():
    assert command_line.main is cli.main
    assert command_line.get_export_path_and_channel_id is cli.get_export_path_and_channel_id


def test_module_main_invokes_cli_main(monkeypatch):
    called = {"value": False}

    def _fake_main():
        called["value"] = True

    monkeypatch.setattr("slackdump2html.cli.main", _fake_main)
    runpy.run_module("slackdump2html.__main__", run_name="__main__")

    assert called["value"] is True
