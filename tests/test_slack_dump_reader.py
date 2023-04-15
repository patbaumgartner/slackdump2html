import json
from pathlib import Path

from slackdump2html.HtmlPrinter import HtmlPrinter
from slackdump2html.SlackDataCleaner import SlackDataCleaner
from slackdump2html.SlackDumpReader import SlackDumpReader


def _prepare_test_workspace(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    (data_dir / "emojis" / "emojis").mkdir(parents=True)

    (data_dir / "users.txt").write_text(
        "name id\n---- ----\nJane.Doe U123\n",
        encoding="utf-8",
    )
    (data_dir / "channels.txt").write_text(
        "id name\nC2R198BRC #general\n",
        encoding="utf-8",
    )
    (data_dir / "emojis" / "index.json").write_text("{}", encoding="utf-8")

    export_file = tmp_path / "C2R198BRC.json"
    export_file.write_text(
        json.dumps(
            {
                "name": "general",
                "messages": [
                    {
                        "type": "message",
                        "user": "U123",
                        "text": "Hello world",
                        "ts": "1710000000.000100",
                    },
                    {
                        "type": "message",
                        "user": "U123",
                        "blocks": [
                            {
                                "type": "section",
                                "text": {"type": "mrkdwn", "text": "Block only message"},
                            }
                        ],
                        "ts": "1710000001.000100",
                    },
                    {
                        "type": "message",
                        "subtype": "channel_join",
                        "user": "U123",
                        "text": "<@U123> has joined the channel",
                        "metadata": {"event_type": "invitee_joined_channel"},
                        "ts": "1710000002.000100",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return export_file


def test_slack_dump_reader_reads_messages(tmp_path: Path, monkeypatch):
    export_file = _prepare_test_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    reader = SlackDumpReader(SlackDataCleaner())
    data = reader.read(str(export_file))

    assert data.channel_name == "general"
    assert len(data.messages) == 3
    assert data.messages[0].text == "Hello world"
    assert "Block only message" in data.messages[1].text
    assert data.messages[2].subtype == "channel join"
    assert data.messages[2].metadata_event_type == "invitee joined channel"


def test_html_printer_writes_output_file(tmp_path: Path, monkeypatch):
    export_file = _prepare_test_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    reader = SlackDumpReader(SlackDataCleaner())
    data = reader.read(str(export_file))
    data.channel_name = "test-channel"
    printer = HtmlPrinter(data, "C2R198BRC")

    printer.print()

    output = tmp_path / "out" / "test-channel.html"
    assert output.exists()
    assert "Hello world" in output.read_text(encoding="utf-8")
