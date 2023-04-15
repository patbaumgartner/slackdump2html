import json
from datetime import datetime
from typing import Any

from slackdump2html.data_structures import ChannelType, SlackData, SlackMessage, SlackThreadMessage
from slackdump2html.SlackDataCleaner import SlackDataCleaner
from slackdump2html.SlackDumpReader import SlackDumpReader


def _write_data_files(tmp_path):
    data_dir = tmp_path / "data"
    (data_dir / "emojis" / "emojis").mkdir(parents=True)
    (data_dir / "emojis" / "index.json").write_text("{}", encoding="utf-8")
    (data_dir / "users.txt").write_text(
        "name id\n---- ----\nJane.Doe U123\nJohn U456\n",
        encoding="utf-8",
    )
    (data_dir / "channels.txt").write_text(
        "id name\nC123 #general\nP123 🔒private\n",
        encoding="utf-8",
    )


def test_cleaner_name_and_emoji_helpers(tmp_path, monkeypatch):
    _write_data_files(tmp_path)
    monkeypatch.chdir(tmp_path)

    cleaner = SlackDataCleaner()

    assert cleaner.get_user_name("U123") == "Jane Doe"
    assert cleaner.get_user_name("UNKNOWN") == "UNKNOWN"
    assert cleaner.to_pretty_user("john") == "john"
    assert cleaner.replace_emoji_name("hand") == "raised_hand"
    assert cleaner.replace_emoji_name("thumbsup") == "thumbs_up"
    assert cleaner.replace_emoji_name_with_skin_tone("wave", 2) == "wave_light_skin_tone"


def test_cleaner_replace_names_updates_messages(tmp_path, monkeypatch):
    _write_data_files(tmp_path)
    monkeypatch.chdir(tmp_path)

    cleaner = SlackDataCleaner()
    data = SlackData(
        channel_type=ChannelType.Channel,
        channel_name="general",
        emojis={},
        messages=[
            SlackMessage(
                user="U123",
                text="hello",
                date=datetime.now(),
                reactions={},
                replies=[
                    SlackThreadMessage(
                        user="U456",
                        text="reply",
                        date=datetime.now(),
                        reactions={},
                    )
                ],
            )
        ],
    )

    cleaner.replace_names(data)

    assert data.messages[0].user == "Jane Doe"
    assert data.messages[0].replies[0].user == "John"


def test_reader_helper_methods(tmp_path, monkeypatch):
    _write_data_files(tmp_path)
    monkeypatch.chdir(tmp_path)

    cleaner = SlackDataCleaner()
    reader = SlackDumpReader(cleaner)

    assert reader.get_channel_name({"name": "ignored"}, "C123") == (
        ChannelType.Channel,
        "general",
    )
    assert reader.get_channel_name({"name": ""}, "UNKNOWN") == (
        ChannelType.Unknown,
        "UNKNOWN",
    )
    assert reader.get_channel_name({"name": "abc"}, "X") == (ChannelType.Channel, "abc")

    assert reader.get_user({"user": "U123"}) == "U123"
    assert reader.get_user({}) == "Unknown user"

    assert reader.is_gif({}) is False
    assert (
        reader.is_gif(
            {
                "blocks": [
                    {
                        "type": "image",
                        "image_url": "https://media.giphy.com/media/demo/giphy.gif",
                    }
                ]
            }
        )
        is True
    )

    assert reader.read_reactions({"reactions": [{"name": "wave", "count": 3}]}) == {"wave": 3}
    assert reader.read_reactions({}) == {}

    gif_path = tmp_path / "data" / "emojis" / "emojis" / "party.gif"
    gif_path.write_bytes(b"GIF89a")
    assert reader.get_emoji_file_name("party").endswith("party.gif")
    assert reader.get_emoji_file_name("missing").startswith("<none>")

    assert reader.get_image_type(b"GIF89a") == "image/gif"
    assert reader.get_image_type(b"PNG") == "image/png"
    assert isinstance(reader.to_datetime("1710000000.000100"), datetime)


def test_reader_read_replies_filters_invalid(tmp_path, monkeypatch):
    _write_data_files(tmp_path)
    monkeypatch.chdir(tmp_path)

    reader = SlackDumpReader(SlackDataCleaner())
    message = {
        "slackdump_thread_replies": [
            {"type": "message", "user": "U123", "text": "ok", "ts": "1"},
            {"type": "message", "subtype": "bot_message", "text": "skip", "ts": "1"},
            {"type": "something_else", "text": "skip", "ts": "1"},
        ]
    }

    replies = reader.read_replies(message)

    assert len(replies) == 1
    assert replies[0].text == "ok"


def test_cleaner_reads_users_json_with_avatar(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    (data_dir / "emojis" / "emojis").mkdir(parents=True)
    (data_dir / "emojis" / "index.json").write_text("{}", encoding="utf-8")
    (data_dir / "channels.txt").write_text("id name\nC123 #general\n", encoding="utf-8")
    (data_dir / "users.json").write_text(
        '[{"id":"U123","name":"jane.doe","real_name":"Jane Doe",'
        '"profile":{"display_name":"Jane","image_72":"https://example.com/avatar.png"}}]',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    cleaner = SlackDataCleaner()

    assert cleaner.get_user_name("U123") == "Jane"
    assert cleaner.get_user_avatar("U123") == "https://example.com/avatar.png"


def test_cleaner_resolves_handle_names_to_display_name(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    (data_dir / "emojis" / "emojis").mkdir(parents=True)
    (data_dir / "emojis" / "index.json").write_text("{}", encoding="utf-8")
    (data_dir / "channels.txt").write_text("id name\nC123 #general\n", encoding="utf-8")
    (data_dir / "users.json").write_text(
        '[{"id":"U123","name":"jane.doe","profile":{"display_name":"Jane D","image_72":"https://example.com/a.png"}}]',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    cleaner = SlackDataCleaner()

    assert cleaner.get_user_name("jane.doe") == "Jane D"
    assert cleaner.get_user_name("JANE.DOE") == "Jane D"
    assert cleaner.get_user_avatar("jane.doe") == "https://example.com/a.png"


def test_cleaner_handles_missing_user_and_channel_files(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    (data_dir / "emojis" / "emojis").mkdir(parents=True)
    (data_dir / "emojis" / "index.json").write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    cleaner = SlackDataCleaner()

    assert cleaner.get_user_name("U123") == "U123"
    assert cleaner.channel_map == {}


def test_reader_handles_missing_emoji_index(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    reader = SlackDumpReader(SlackDataCleaner())

    assert reader.read_emojis() == {}


def test_reader_collects_shared_images_from_message_sections(tmp_path, monkeypatch):
    _write_data_files(tmp_path)
    monkeypatch.chdir(tmp_path)

    reader = SlackDumpReader(SlackDataCleaner())
    message = {
        "text": "Look at this",
        "blocks": [{"type": "image", "image_url": "https://example.com/block.png"}],
        "files": [{"mimetype": "image/jpeg", "url_private": "https://example.com/file.jpg"}],
        "attachments": [{"image_url": "https://example.com/att.webp"}],
    }

    content = reader.get_message_content(message)

    assert "shared-image" in content
    assert "shared-image-link" in content
    assert "https://example.com/block.png" in content
    assert "https://example.com/file.jpg" in content
    assert "https://example.com/att.webp" in content


def test_reader_normalizes_local_file_images_for_preview(tmp_path, monkeypatch):
    _write_data_files(tmp_path)
    monkeypatch.chdir(tmp_path)

    reader = SlackDumpReader(SlackDataCleaner())
    message = {
        "text": "",
        "files": [{"mimetype": "image/jpeg", "url_private": "C2R198BRC/F01-photo.jpg"}],
    }

    content = reader.get_message_content(message)

    assert "../data/messages/C2R198BRC/F01-photo.jpg" in content
    assert "Open image" in content


def test_reader_collects_reaction_users_and_file_cards(tmp_path, monkeypatch):
    _write_data_files(tmp_path)
    monkeypatch.chdir(tmp_path)

    reader = SlackDumpReader(SlackDataCleaner())
    message = {
        "text": "",
        "reactions": [{"name": "+1", "count": 2, "users": ["U123", "U456"]}],
        "files": [
            {
                "title": "Architecture.pdf",
                "pretty_type": "PDF",
                "size": 4096,
                "permalink": "https://example.com/Architecture.pdf",
            }
        ],
        "attachments": [
            {
                "title": "Related Link",
                "text": "Background context",
                "title_link": "https://example.com/context",
            }
        ],
    }

    reaction_users = reader.read_reaction_users(message)
    content = reader.get_message_content(message)

    assert reaction_users == {"+1": ["U123", "U456"]}
    assert "file-card" in content
    assert "Architecture.pdf" in content
    assert "Related Link" in content


def test_reader_renders_video_and_pdf_previews(tmp_path, monkeypatch):
    _write_data_files(tmp_path)
    monkeypatch.chdir(tmp_path)

    reader = SlackDumpReader(SlackDataCleaner())
    message = {
        "files": [
            {
                "title": "Demo Video",
                "mimetype": "video/mp4",
                "permalink": "https://example.com/video.mp4",
            },
            {
                "title": "Slides",
                "mimetype": "application/pdf",
                "url_private": "C1/F2-slides.pdf",
            },
        ]
    }

    content = reader.get_message_content(message)

    assert "shared-video-player" in content
    assert "video.mp4" in content
    assert "shared-pdf-embed" in content
    assert "Open PDF" in content


def test_reader_parses_optional_message_state_fields(tmp_path, monkeypatch):
    _write_data_files(tmp_path)
    monkeypatch.chdir(tmp_path)

    reader = SlackDumpReader(SlackDataCleaner())
    message = {
        "type": "message",
        "user": "U123",
        "text": "stateful",
        "ts": "1710000000.000100",
        "subscribed": True,
        "last_read": "1710000001.000100",
        "upload": True,
        "team": "T123",
        "client_msg_id": "abc-123",
    }

    data = {"name": "general", "messages": [message]}
    file_path = tmp_path / "C123.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    slack_data = reader.read(str(file_path))
    parsed = slack_data.messages[0]

    assert parsed.subscribed is True
    assert parsed.last_read is not None
    assert parsed.upload is True
    assert parsed.team_id == "T123"
    assert parsed.client_msg_id == "abc-123"


def test_reader_extracts_text_from_rich_text_blocks(tmp_path, monkeypatch):
    _write_data_files(tmp_path)
    monkeypatch.chdir(tmp_path)

    reader = SlackDumpReader(SlackDataCleaner())
    message = {
        "blocks": [
            {
                "type": "rich_text",
                "elements": [
                    {
                        "type": "rich_text_section",
                        "elements": [
                            {"type": "text", "text": "Hello "},
                            {"type": "user", "user_id": "U123"},
                            {"type": "text", "text": "!"},
                        ],
                    }
                ],
            }
        ]
    }

    assert reader.get_message_text(message) == "Hello <@U123>!"


def test_reader_extract_text_helpers_cover_rich_variants(tmp_path, monkeypatch):
    _write_data_files(tmp_path)
    monkeypatch.chdir(tmp_path)

    reader = SlackDumpReader(SlackDataCleaner())

    elements: list[Any] = [
        "skip-non-dict",
        {"type": "plain_text", "text": "A"},
        {"type": "emoji", "name": "wave"},
        {"type": "link", "url": "https://example.com", "text": "Example"},
        {"type": "link", "url": "https://example.org"},
        {"type": "user", "user_id": "U123"},
        {"type": "broadcast", "range": "here"},
        {"type": "channel", "channel_id": "C123", "name": "general"},
        {"type": "channel", "channel_id": "C456"},
        {
            "type": "rich_text_section",
            "elements": [{"type": "text", "text": " nested"}],
        },
        {
            "type": "rich_text_list",
            "style": "ordered",
            "elements": [
                {
                    "elements": [
                        {"type": "text", "text": "first"},
                    ]
                },
                "invalid-item",
            ],
        },
        {"type": "button", "text": {"type": "plain_text", "text": "Run"}},
    ]

    extracted = reader.extract_text_from_elements(elements)  # type: ignore[arg-type]

    assert "A" in extracted
    assert ":wave:" in extracted
    assert "<https://example.com|Example>" in extracted
    assert "<https://example.org>" in extracted
    assert "<@U123>" in extracted
    assert "<!here>" in extracted
    assert "<#C123|general>" in extracted
    assert "<#C456|C456>" in extracted
    assert "1. first" in extracted
    assert "Run" in extracted


def test_reader_extract_text_from_blocks_variants(tmp_path, monkeypatch):
    _write_data_files(tmp_path)
    monkeypatch.chdir(tmp_path)

    reader = SlackDumpReader(SlackDataCleaner())
    blocks: list[Any] = [
        "skip",
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "Section text"},
            "fields": [
                {"type": "mrkdwn", "text": "Field text"},
                "ignore-me",
            ],
        },
        {
            "type": "context",
            "elements": [{"type": "text", "text": "Context text"}],
        },
        {
            "type": "actions",
            "elements": [{"type": "button", "text": {"type": "plain_text", "text": "Click"}}],
        },
    ]

    extracted = reader.extract_text_from_blocks(blocks)  # type: ignore[arg-type]

    assert "Section text" in extracted
    assert "Field text" in extracted
    assert "Context text" in extracted
    assert "Click" in extracted


def test_reader_message_text_and_misc_paths(tmp_path, monkeypatch):
    _write_data_files(tmp_path)
    monkeypatch.chdir(tmp_path)

    reader = SlackDumpReader(SlackDataCleaner())

    assert reader.get_message_text({"text": "direct"}) == "direct"
    assert reader.get_message_text({"blocks": "not-a-list"}) == ""
    assert reader.normalize_media_url(None) is None
    assert reader.normalize_media_url("   ") is None
    assert reader.normalize_media_url("https://example.com/a.png") == "https://example.com/a.png"
    assert reader.normalize_media_url("/tmp/image.png") == "/tmp/image.png"

    avatar = reader.get_avatar_url(
        {"user_profile": {"image_72": "https://example.com/avatar.png"}}, "UNKNOWN"
    )
    assert avatar == "https://example.com/avatar.png"

    reaction_users = reader.read_reaction_users(
        {
            "reactions": [
                "invalid",
                {"name": "+1", "users": "invalid"},
                {"name": "+1", "users": ["U123", 42]},
            ]
        }
    )
    assert reaction_users == {"+1": ["U123"]}


def test_reader_image_and_attachment_path_variants(tmp_path, monkeypatch):
    _write_data_files(tmp_path)
    monkeypatch.chdir(tmp_path)

    reader = SlackDumpReader(SlackDataCleaner())
    message = {
        "blocks": ["invalid", {"type": "image", "image_url": "https://example.com/block.jpg"}],
        "files": [
            "invalid",
            {"mimetype": "text/plain", "url_private": "C1/F1.txt"},
            {"mimetype": "image/png", "url_private": "C1/F2.png"},
        ],
        "attachments": [
            "invalid",
            {"thumb_url": "https://example.com/thumb.jpg"},
        ],
    }

    urls = reader.get_shared_image_urls(message)

    assert "https://example.com/block.jpg" in urls
    assert "../data/messages/C1/F2.png" in urls
    assert "https://example.com/thumb.jpg" in urls


def test_reader_emoji_alias_and_extension_resolution(tmp_path, monkeypatch):
    _write_data_files(tmp_path)
    monkeypatch.chdir(tmp_path)

    emoji_base = tmp_path / "data" / "emojis" / "emojis"
    index_file = tmp_path / "data" / "emojis" / "index.json"
    (emoji_base / "party.png").write_bytes(b"PNG")
    (emoji_base / "photo.jpeg").write_bytes(b"JPEG")
    (emoji_base / "scan.jpg").write_bytes(b"JPG")
    index_file.write_text('{"party":"party.png","party_alias":"alias:party"}', encoding="utf-8")

    reader = SlackDumpReader(SlackDataCleaner())
    emojis = reader.read_emojis()

    assert "party" in emojis
    assert emojis["party_alias"] == emojis["party"]
    assert reader.get_emoji_file_name("photo").endswith("photo.jpeg")
    assert reader.get_emoji_file_name("scan").endswith("scan.jpg")
