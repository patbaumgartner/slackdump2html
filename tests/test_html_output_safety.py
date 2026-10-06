"""Regression tests: dump content must never reach the published HTML unescaped.

A slackdump export is attacker-influenced (any workspace member can post the
content), and the generated file is published on a web server. These tests pin
the escaping behaviour of every sink that interpolates dump content.
"""

import json
import re
import sys

from slackdump2html import cli
from slackdump2html.data_structures import ChannelType, SlackData
from slackdump2html.HtmlPrinter import HtmlPrinter
from slackdump2html.SlackDataCleaner import SlackDataCleaner
from slackdump2html.SlackDumpReader import SlackDumpReader


def _printer(channel_name="general", emojis=None):
    data = SlackData(
        channel_type=ChannelType.Channel,
        channel_name=channel_name,
        messages=[],
        emojis=emojis or {},
    )
    return HtmlPrinter(data, "C1")


def test_message_text_is_escaped():
    html = _printer().format_message("<script>alert(1)</script> and <img src=x onerror=alert(2)>")
    assert "<script>" not in html
    assert "<img src=x" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_quotes_and_ampersands_are_escaped():
    html = _printer().format_message('say "hi" & <b>bye</b>')
    assert "<b>bye</b>" not in html
    assert "&quot;hi&quot;" in html
    assert "&amp;" in html


def test_code_blocks_keep_literal_content():
    html = _printer().format_message("```\n*raw* :smile: <b>x</b>\n```")
    assert "<b>raw</b>" not in html
    assert ":smile:" in html
    assert "&lt;b&gt;x&lt;/b&gt;" in html
    assert html.startswith("<code>")


def test_link_alias_renders_emoji_but_no_other_formatting():
    html = _printer().format_message("<https://ex.com/a.png|pic :smile: *x*>")
    # emoji aliases in link text render, like Slack does
    assert '<a href="https://ex.com/a.png">pic 😄 *x*</a>' in html
    # other message formatting does not apply to link text
    assert "<b>x</b>" not in html
    # the image preview keeps a plain-text label
    assert 'alt="pic :smile: *x*"' in html


def test_emoji_alias_in_link_href_is_untouched():
    html = _printer().format_message("<https://ex.com/q/:zap:/here|label :zap:>")
    assert '<a href="https://ex.com/q/:zap:/here">' in html
    assert "label ⚡" in html


def test_markup_still_renders():
    html = _printer().format_message(
        "<!here> <!channel> <@U1> <#C1|general> *bold* <https://ex.com|t>"
    )
    assert '<span class="user-mention">here</span>' in html
    assert '<span class="user-mention">channel</span>' in html
    assert '<span class="user-mention">U1</span>' in html
    assert '<span class="channel-mention">general</span>' in html
    assert "<b>bold</b>" in html
    assert '<a href="https://ex.com">t</a>' in html


def test_channel_name_is_escaped_in_heading_and_title(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    printer = _printer(channel_name="<img src=x onerror=alert(8)>")
    printer.print()

    html = (tmp_path / "out" / "_img_src_x_onerror_alert_8__.html").read_text(encoding="utf-8")
    assert "<img src=x" not in html
    assert "&lt;img src=x onerror=alert(8)&gt;" in html


def test_output_file_name_is_sanitized():
    assert HtmlPrinter.safe_output_name("socrates_ch") == "socrates_ch"
    assert HtmlPrinter.safe_output_name("..") == "channel"
    assert HtmlPrinter.safe_output_name("") == "channel"
    assert "/" not in HtmlPrinter.safe_output_name("a/b")
    assert "<" not in HtmlPrinter.safe_output_name("<x>")


def test_reaction_emoji_name_is_escaped():
    printer = _printer(emojis={})
    html = printer.get_custom_emoji_html("<script>alert(4)</script>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_emoji_css_class_is_sanitized():
    name = 'evil"><script>x'
    printer = _printer(emojis={name: "image/png;base64,AAA"})
    html = printer.get_custom_emoji_html(name)
    css_class = HtmlPrinter.emoji_class_name(name)
    assert html == f'<i class="emoji emoji-{css_class}"></i>'
    assert re.fullmatch(r"[\w+-]+", css_class)
    assert "<" not in html.split("emoji emoji-")[1].split('"')[0]


def test_emoji_data_url_is_validated():
    assert HtmlPrinter.safe_data_url("image/png;base64,AAAA")
    assert HtmlPrinter.safe_data_url("image/gif;base64,AAAA+/=")
    assert not HtmlPrinter.safe_data_url('x"){}@import url("//evil");')
    assert not HtmlPrinter.safe_data_url("image/png;base64,AAAA)</style>")


def test_emoji_definitions_skip_unsafe_data_and_are_sorted():
    printer = _printer(emojis={"party": "image/png;base64,AAA", "bad": 'x";}'})
    printer.used_custom_emojis.update(["party", "bad"])
    html = printer.print_custom_emoji_definitions()
    assert ".emoji-party {" in html
    assert 'url("data:image/png;base64,AAA")' in html
    # unsafe data URL must not reach the stylesheet
    assert 'x";}' not in html
    # deterministic output regardless of set iteration order
    printer.used_custom_emojis.clear()
    printer.used_custom_emojis.update(["party", "bad"])
    assert html == printer.print_custom_emoji_definitions()


def test_empty_user_name_does_not_crash():
    printer = _printer()
    for user in ("", " ", "  a  ", "Jane Doe"):
        assert "user-image" in printer.print_user_image(user)


def test_end_to_end_hostile_dump_is_escaped(tmp_path, monkeypatch):
    export = tmp_path / "export"
    export.mkdir()
    dump = {
        "name": "<img src=x onerror=alert(8)>",
        "channel_id": "C9",
        "messages": [
            {
                "type": "message",
                "user": "<b>evil</b>",
                "text": "<script>alert('xss1')</script>",
                "ts": "1700000000.000100",
                "reactions": [
                    {
                        "name": "<script>alert(4)</script>",
                        "count": 1,
                        "users": ["U1"],
                    }
                ],
            }
        ],
    }
    (export / "C9.json").write_text(json.dumps(dump), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["slackdump2html", str(export), "C9"])
    cli.main()

    out_files = list((tmp_path / "out").glob("*.html"))
    assert len(out_files) == 1
    html = out_files[0].read_text(encoding="utf-8")

    assert "<script>" not in html
    assert "<img src=x" not in html
    assert "<b>evil</b>" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;script&gt;alert(&#x27;xss1&#x27;)&lt;/script&gt;" in html
    assert '<p class="message">' in html
    assert out_files[0].name == "_img_src_x_onerror_alert_8__.html"


def test_reader_markup_survives_while_text_is_escaped(tmp_path, monkeypatch):
    export = tmp_path / "export"
    export.mkdir()
    dump = {
        "name": "cards",
        "channel_id": "C1",
        "messages": [
            {
                "type": "message",
                "user": "U1",
                "ts": "1700000000.000100",
                "text": "<script>alert(1)</script> and *bold* :zap:",
                "attachments": [
                    {
                        "title": "Site :zap:",
                        "text": "Description",
                        "title_link": "https://ex.com",
                    }
                ],
                "files": [
                    {
                        "title": "<b>evil</b>",
                        "name": "x.png",
                        "size": 2048,
                        "pretty_type": "PNG",
                        "permalink": "https://ex.com/x.png",
                        "mimetype": "image/png",
                    }
                ],
            }
        ],
    }
    (export / "C1.json").write_text(json.dumps(dump), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    data = SlackDumpReader(SlackDataCleaner()).read(str(export / "C1.json"))
    body = HtmlPrinter(data, "C1").message_body(data.messages[0])

    # reader-generated markup must survive (it is already escaped by the reader)
    assert '<article class="file-card">' in body
    # untrusted dump text must be escaped
    assert "<script>" not in body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    assert "&lt;b&gt;evil&lt;/b&gt;" in body
    # Slack text formatting and emoji aliases still render
    assert "<b>bold</b>" in body
    assert "⚡" in body
    # cards are not run through the message formatter
    assert "<b>evil</b>" not in body
