from datetime import datetime

from slackdump2html.data_structures import ChannelType, SlackData, SlackMessage, SlackThreadMessage
from slackdump2html.HtmlPrinter import HtmlPrinter


def _prepare(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    (data_dir / "emojis" / "emojis").mkdir(parents=True)
    (data_dir / "users.txt").write_text(
        "name id\n---- ----\nJane.Doe U123\n",
        encoding="utf-8",
    )
    (data_dir / "channels.txt").write_text(
        "id name\nC1 #general\n",
        encoding="utf-8",
    )
    (data_dir / "emojis" / "index.json").write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)


def _message(user="U123", text="hello"):
    return SlackMessage(
        user=user,
        text=text,
        date=datetime(2024, 1, 1, 10, 20, 30),
        reactions={},
        replies=[],
    )


def test_html_helper_outputs(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)

    data = SlackData(
        channel_type=ChannelType.Channel,
        channel_name="general",
        messages=[_message()],
        emojis={"custom": "image/png;base64,abc"},
    )
    printer = HtmlPrinter(data, "C1")

    assert "date-block" in printer.print_date_block("Mon")
    assert "user-image" in printer.print_user_image("Jane Doe")
    assert printer.calc_color_num("User") in range(15)

    assert '<a href="https://example.com">Title</a>' in printer.format_message(
        "<https://example.com|Title>"
    )
    assert "<b>bold</b>" in printer.format_message("*bold*")
    assert "<code>&lt;tag&gt;</code>" in printer.format_message("```<tag>```")
    assert "channel-mention" in printer.format_message("<#C1|general>")


def test_html_reactions_replies_and_custom_emoji(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)

    reply = SlackThreadMessage(
        user="U123",
        text="reply",
        date=datetime(2024, 1, 1, 10, 22, 0),
        reactions={"custom": 1},
    )
    msg = SlackMessage(
        user="U123",
        text=":custom:",
        date=datetime(2024, 1, 1, 10, 20, 30),
        reactions={"custom": 2},
        replies=[reply],
    )
    data = SlackData(
        channel_type=ChannelType.Channel,
        channel_name="general",
        messages=[msg],
        emojis={"custom": "image/png;base64,abc"},
    )

    printer = HtmlPrinter(data, "C1")
    message_html = printer.print_message(msg)
    defs_html = printer.print_custom_emoji_definitions()

    assert "reactions" in message_html
    assert "thread" in message_html
    assert "emoji-custom" in message_html
    assert "background-image" in defs_html


def test_html_print_writes_file(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)

    data = SlackData(
        channel_type=ChannelType.Channel,
        channel_name="general",
        messages=[_message(text="Hello")],
        emojis={},
    )

    printer = HtmlPrinter(data, "C1")
    printer.print()

    output_file = tmp_path / "out" / "general.html"
    assert output_file.exists()
    html = output_file.read_text(encoding="utf-8")
    assert "general chat history" in html
    assert "Hello" in html


def test_html_prints_avatar_image_when_available(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)

    data = SlackData(
        channel_type=ChannelType.Channel,
        channel_name="general",
        messages=[
            SlackMessage(
                user="Jane Doe",
                text="Hello",
                date=datetime(2024, 1, 1, 10, 20, 30),
                reactions={},
                replies=[],
                avatar_url="https://example.com/avatar.jpg",
            )
        ],
        emojis={},
    )

    printer = HtmlPrinter(data, "C1")
    html = printer.print_message(data.messages[0])

    assert "user-avatar-img" in html
    assert "https://example.com/avatar.jpg" in html


def test_html_embeds_image_links(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)

    data = SlackData(
        channel_type=ChannelType.Channel,
        channel_name="general",
        messages=[_message()],
        emojis={},
    )
    printer = HtmlPrinter(data, "C1")

    html = printer.format_message("<https://example.com/pic.png|image>")

    assert "shared-image-img" in html
    assert "https://example.com/pic.png" in html


def test_html_shows_who_reacted_and_edited_badge(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)

    data = SlackData(
        channel_type=ChannelType.Channel,
        channel_name="general",
        messages=[
            SlackMessage(
                user="Jane Doe",
                text="Thanks",
                date=datetime(2024, 1, 1, 10, 20, 30),
                reactions={"+1": 2},
                reaction_users={"+1": ["U123"]},
                replies=[],
                edited=True,
            )
        ],
        emojis={},
    )

    printer = HtmlPrinter(data, "C1")
    html = printer.print_message(data.messages[0])

    assert "edited-label" in html
    assert "Liked by: Jane Doe" in html


def test_html_shows_subtype_and_metadata_badges(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)

    data = SlackData(
        channel_type=ChannelType.Channel,
        channel_name="general",
        messages=[
            SlackMessage(
                user="Jane Doe",
                text="Joined",
                date=datetime(2024, 1, 1, 10, 20, 30),
                reactions={},
                replies=[],
                subtype="channel join",
                metadata_event_type="invitee joined channel",
            )
        ],
        emojis={},
    )

    printer = HtmlPrinter(data, "C1")
    html = printer.print_message(data.messages[0])

    assert "subtype-badge" in html
    assert "metadata-badge" in html
    assert "channel join" in html
    assert "invitee joined channel" in html


def test_html_shows_read_state_and_upload_badges(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)

    data = SlackData(
        channel_type=ChannelType.Channel,
        channel_name="general",
        messages=[
            SlackMessage(
                user="Jane Doe",
                text="State",
                date=datetime(2024, 1, 1, 10, 20, 30),
                reactions={},
                replies=[],
                subscribed=True,
                last_read=datetime(2024, 1, 1, 10, 30, 0),
                upload=True,
                team_id="T123",
                client_msg_id="abc-123",
            )
        ],
        emojis={},
    )

    printer = HtmlPrinter(data, "C1")
    html = printer.print_message(data.messages[0])

    assert "state-badge" in html
    assert "subscribed" in html
    assert "last read 01.01.2024 10:30:00" in html
    assert "upload" in html
    assert "team T123" in html
    assert "client abc-123" in html
