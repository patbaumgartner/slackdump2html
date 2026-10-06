import re
import runpy
import subprocess
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


def test_usage_error_exits_2_with_usage_on_stderr(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 2
    captured = capsys.readouterr()
    assert "error: Please provide an export folder and a channel ID." in captured.err
    assert "usage: slackdump2html <export-folder> <channel-id>" in captured.err
    assert captured.out == ""


def test_missing_export_folder_exits_2(monkeypatch, capsys, tmp_path: Path):
    monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path / "nope"), "C1"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 2
    assert "existing export folder" in capsys.readouterr().err


def test_help_exits_0_with_description(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog", "--help"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: slackdump2html" in captured.out
    assert "self-contained HTML" in captured.out


def test_version_exits_0(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog", "--version"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 0
    assert re.match(r"slackdump2html \d+\.\d+", capsys.readouterr().out.strip())


def test_missing_channel_file_exits_1_without_traceback(monkeypatch, capsys, tmp_path: Path):
    monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path), "CNOPE"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 1
    captured = capsys.readouterr()
    assert f"export file not found: {tmp_path}/CNOPE.json" in captured.err
    assert "Traceback" not in captured.err


def test_malformed_json_exits_1(monkeypatch, capsys, tmp_path: Path):
    (tmp_path / "C1.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path), "C1"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 1
    assert "is not valid JSON" in capsys.readouterr().err


def test_wrong_json_shape_exits_1(monkeypatch, capsys, tmp_path: Path):
    (tmp_path / "C1.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path), "C1"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 1
    assert "does not look like a slackdump export" in capsys.readouterr().err


def test_cli_reports_usage_errors_without_a_traceback():
    result = subprocess.run(
        [sys.executable, "-m", "slackdump2html"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert "usage: slackdump2html" in result.stderr
