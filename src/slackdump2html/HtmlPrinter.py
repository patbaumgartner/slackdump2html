import importlib.resources as pkg_resources
import os
import re
from datetime import datetime
from html import escape

import emoji

from slackdump2html.SlackDataCleaner import SlackDataCleaner
from slackdump2html.SlackDumpReader import SlackData, SlackMessage, SlackThreadMessage

from . import styles


class HtmlPrinter:
    slack_data: SlackData
    channel_id: str
    used_custom_emojis: set[str]
    data_cleaner: SlackDataCleaner

    def __init__(self, slack_data: SlackData, channel_id: str):
        self.slack_data = slack_data
        self.channel_id = channel_id
        self.used_custom_emojis = set()
        self.data_cleaner = SlackDataCleaner()

    def print(self):
        title_text = escape(self.slack_data.get_title_text(), quote=True)
        html1 = "<!DOCTYPE html>\n"
        html1 += "    <head>\n"
        html1 += f"        <title>{title_text} chat history</title>\n"
        html1 += '        <meta charset="UTF-8">'
        html1 += self.read_css_file()
        html3 = "    </head>\n"
        html3 += "    <body>\n"
        html3 += f"        <h1>{title_text} chat history</h1>\n"
        html3 += self.print_messages(self.slack_data.messages)
        # Only print used emojis
        html2 = self.print_custom_emoji_definitions()
        html3 += "    </body>\n"
        html3 += "</html>\n"

        html = html1 + html2 + html3

        self.write_out_file(html)

    def read_css_file(self) -> str:
        html = '        <style type="text/css">\n'
        html += pkg_resources.read_text(styles, "style.css")
        html += "        </style>\n"
        return html

    def print_messages(self, messages: list[SlackMessage]) -> str:
        html = ""

        last_date = None
        if len(messages) > 0:
            last_date = self.to_date(messages[0].date)
            html += self.print_date_block(last_date)

        for message in messages:
            date = self.to_date(message.date)
            if date != last_date:
                last_date = date
                html += self.print_date_block(date)

            html += self.print_message(message)
        return html

    def print_date_block(self, date: str) -> str:
        return (
            '        <div class="date-block"><span class="date-block-content">'
            f"{date}</span></div>\n"
        )

    def print_message(self, message: SlackMessage) -> str:
        html = '        <div class="message-container">\n'
        html += self.print_user_image(message.user, message.avatar_url)
        html += '            <p class="meta">\n'
        html += f'                <span class="author">{escape(message.user)}</span>\n'
        if message.edited:
            html += '                <span class="edited-label">edited</span>\n'
        html += self.print_message_badges(
            message.subtype,
            message.metadata_event_type,
            message.subscribed,
            message.last_read,
            message.upload,
            message.team_id,
            message.client_msg_id,
        )
        html += f'                <span class="date">{self.to_time(message.date)}</span>\n'
        html += "            </p>\n"
        html += f'            <p class="message">{self.message_body(message)}</p>\n'
        html += self.print_reactions(message.reactions, message.reaction_users)
        html += self.print_replies(message)
        html += "        </div>\n"
        return html

    def print_user_image(self, user: str, avatar_url: str | None = None) -> str:
        if avatar_url:
            return (
                '            <div class="user-image user-avatar">'
                f'<img src="{escape(avatar_url, quote=True)}" alt="{escape(user)}" '
                'class="user-avatar-img"></div>\n'
            )
        parts = user.split()
        name = "".join(part[0] for part in parts[:2]).upper() if parts else "?"
        return (
            f'            <div class="user-image color{self.calc_color_num(user)}">{name}</div>\n'
        )

    def calc_color_num(self, user: str) -> int:
        letter_sum = 0
        for letter in user:
            letter_sum += ord(letter)
        return letter_sum % 15

    # Placeholder for HTML that is rendered up-front and must survive the
    # formatting rules that run over the literal message text.
    _TOKEN = re.compile(r"\x00(\d+)\x00")

    def message_body(self, message: SlackMessage | SlackThreadMessage) -> str:
        """Render a message body: escaped Slack text plus reader markup.

        ``message.text`` is dump content and goes through ``format_message``,
        which escapes it. ``message.markup`` (shared images, file cards) is
        trusted HTML built by the reader and is inserted as is.
        """
        body = self.format_message(message.text)
        if not message.markup:
            return body
        if body:
            body += "<br>"
        return body + message.markup.replace("\n", "<br>")

    def format_message(self, text: str) -> str:
        """Render Slack mrkdwn text into HTML that is safe to publish.

        Slack markup tokens and fenced code blocks are rendered first and
        stashed, everything else is HTML-escaped, and only then are the
        inline rules applied. The stashed HTML is restored last, so no rule
        can rewrite generated markup and no dump content reaches the output
        unescaped.
        """
        rendered: list[str] = []

        def stash(html: str) -> str:
            rendered.append(html)
            return f"\x00{len(rendered) - 1}\x00"

        # 1. Fenced code blocks keep their content literal.
        text = re.sub(
            r"```(.*?)```",
            lambda match: stash(self.make_code(match.group(1))),
            text,
            flags=re.DOTALL,
        )

        # 2. Slack markup tokens become HTML with per-context escaping.
        text = re.sub(r"<!here>", lambda _match: stash(self.make_broadcast("here")), text)
        text = re.sub(r"<!channel>", lambda _match: stash(self.make_broadcast("channel")), text)
        text = re.sub(
            r"<(http[^<>\s]*)\|([^<>]*)>",
            lambda match: stash(self.create_html_url(match.group(1), match.group(2))),
            text,
        )
        text = re.sub(
            r"<(http[^<>\s]*)>",
            lambda match: stash(self.create_html_url(match.group(1))),
            text,
        )
        text = re.sub(
            r"<@([^<>]*)>",
            lambda match: stash(self.create_at_tag(match.group(1))),
            text,
        )
        text = re.sub(
            r"<#[^<>|]*\|([^<>]*)>",
            lambda match: stash(self.create_channel_tag(match.group(1))),
            text,
        )

        # 3. Whatever is left is literal message text and gets escaped.
        text = escape(text, quote=True)

        # 4. Inline formatting, applied to literal text only.
        text = re.sub(r"\*([^\"\n]+?)\*", self.make_bold, text)
        text = re.sub(r":([\w+-]+?)::skin-tone-(\d):", self.replace_emoji_with_skin_tone, text)
        text = re.sub(r":([\w+-]+?):", self.replace_emoji, text)
        text = text.replace("\n", "<br>")
        text = emoji.emojize(text, language="alias")

        # 5. Restore the pre-rendered HTML.
        return self._TOKEN.sub(lambda match: rendered[int(match.group(1))], text)

    @staticmethod
    def make_bold(match_obj) -> str:
        if match_obj.group(1) is None:
            return match_obj.group(0)
        return f"<b>{match_obj.group(1)}</b>"

    @staticmethod
    def make_code(code: str) -> str:
        return f"<code>{escape(code, quote=True).replace(chr(10), '<br>')}</code>"

    @staticmethod
    def make_broadcast(kind: str) -> str:
        return f'<span class="user-mention">{escape(kind, quote=True)}</span>'

    def create_html_url(self, url: str, alias: str | None = None) -> str:
        safe_url = escape(url, quote=True)
        raw_label = alias if alias is not None else url
        plain_label = escape(raw_label, quote=True)
        label = self.render_label(raw_label)
        if self.is_image_url(url):
            return (
                f'<a href="{safe_url}">{label}</a>'
                f'<br><img src="{safe_url}" alt="{plain_label}" class="shared-image-img">'
            )
        return f'<a href="{safe_url}">{label}</a>'

    def render_label(self, text: str) -> str:
        """Render a link label: escaped text plus emoji aliases, nothing else.

        The label is rendered before the message text is escaped, so it must
        escape itself. Emoji aliases render the way they do in message text;
        other formatting (``*bold*``) is deliberately not applied to link
        text, and the ``href`` is never touched here.
        """
        escaped = escape(text, quote=True)
        escaped = re.sub(
            r":([\w+-]+?)::skin-tone-(\d):",
            self.replace_emoji_with_skin_tone,
            escaped,
        )
        escaped = re.sub(r":([\w+-]+?):", self.replace_emoji, escaped)
        return emoji.emojize(escaped, language="alias")

    def create_at_tag(self, user: str) -> str:
        display_name = self.data_cleaner.user_map.get(user, user)
        return f'<span class="user-mention">{escape(display_name, quote=True)}</span>'

    @staticmethod
    def create_channel_tag(channel_name: str) -> str:
        return f'<span class="channel-mention">{escape(channel_name, quote=True)}</span>'

    def is_image_url(self, url: str) -> bool:
        lowered = url.lower().split("?", 1)[0]
        return lowered.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))

    def replace_emoji(self, match_obj):
        emoji_name = match_obj.group(1)
        if emoji_name is not None:
            return self.get_custom_emoji_html(emoji_name)

    def replace_emoji_with_skin_tone(self, match_obj):
        emoji_name = match_obj.group(1)
        skin_tone = match_obj.group(2)
        if emoji_name is not None and skin_tone is not None:
            cleaned_emoji_name = self.data_cleaner.replace_emoji_name_with_skin_tone(
                emoji_name, int(skin_tone)
            )
            return self.get_custom_emoji_html(cleaned_emoji_name)

    def print_reactions(
        self,
        reactions: dict[str, int],
        reaction_users: dict[str, list[str]],
    ) -> str:
        html = ""
        if len(reactions) > 0:
            html += '            <ul class="reactions">\n'
            for reaction in reactions.items():
                emoji_name = self.get_custom_emoji_html(reaction[0])
                if emoji_name.startswith(":"):
                    print(f"Couldn't translate emoji {emoji_name}")
                users = reaction_users.get(reaction[0], [])
                users_display = [self.data_cleaner.get_user_name(user) for user in users]
                users_title = (
                    f"Liked by: {', '.join(users_display)}" if users_display else reaction[0]
                )
                html += (
                    f'                <li title="{escape(users_title, quote=True)}">{emoji_name} '
                    f"{reaction[1]}</li>\n"
                )
            html += "            </ul>\n"
        return html

    def get_custom_emoji_html(self, emoji_name: str) -> str:
        if emoji_name in self.slack_data.emojis:
            self.used_custom_emojis.add(emoji_name)
            return f'<i class="emoji emoji-{self.emoji_class_name(emoji_name)}"></i>'
        return escape(
            emoji.emojize(
                f":{self.data_cleaner.replace_emoji_name(emoji_name)}:",
                language="alias",
            ),
            quote=True,
        )

    @staticmethod
    def emoji_class_name(emoji_name: str) -> str:
        """Map an emoji name onto a CSS/HTML class fragment that cannot escape
        the class attribute or the generated stylesheet."""
        return re.sub(r"[^\w+-]", "_", emoji_name, flags=re.ASCII) or "_"

    @staticmethod
    def safe_data_url(data: str) -> bool:
        """Only allow base64 image data URIs into the generated stylesheet."""
        return bool(re.fullmatch(r"image/[a-z0-9.+-]+;base64,[A-Za-z0-9+/=]+", data, re.ASCII))

    @staticmethod
    def safe_output_name(channel_name: str) -> str:
        """Derive a portable output file name from a (possibly hostile) name."""
        safe = re.sub(r"[^\w.-]", "_", channel_name).strip(".")
        return safe or "channel"

    def print_replies(self, message: SlackMessage) -> str:
        html = ""
        if len(message.replies) > 0:
            html += '		    <div class="thread">\n'
            html += f'               <p class="thread-meta">{len(message.replies)} answers </p>\n'
            for reply in message.replies:
                html += self.print_reply(reply)
            html += "		    </div>\n"
        return html

    def print_reply(self, reply: SlackThreadMessage) -> str:
        html = '		        <div class="reply">\n'
        html += self.print_user_image(reply.user, reply.avatar_url)
        html += '		            <p class="meta">\n'
        html += f'		                <span class="author">{escape(reply.user)}</span>\n'
        if reply.edited:
            html += '                        <span class="edited-label">edited</span>\n'
        html += self.print_message_badges(
            reply.subtype,
            reply.metadata_event_type,
            team_id=reply.team_id,
            client_msg_id=reply.client_msg_id,
        )
        html += (
            f'		                <span class="date">{self.to_datetime(reply.date)}</span>\n'
        )
        html += "		            </p>\n"
        html += f'		            <p class="message">{self.message_body(reply)}</p>\n'
        html += self.print_reactions(reply.reactions, reply.reaction_users)
        html += "		        </div>\n"
        return html

    def print_custom_emoji_definitions(self) -> str:
        html = '      <style type="text/css">\n'
        for emoji_name in sorted(self.used_custom_emojis):
            data = self.slack_data.emojis[emoji_name]
            if not self.safe_data_url(data):
                continue
            html += f"        .emoji-{self.emoji_class_name(emoji_name)} {{\n"
            html += f'          background-image: url("data:{data}");'
            html += "        }\n"
        html += "      </style>\n"
        return html

    def print_message_badges(
        self,
        subtype: str | None,
        metadata_event_type: str | None,
        subscribed: bool = False,
        last_read: datetime | None = None,
        upload: bool = False,
        team_id: str | None = None,
        client_msg_id: str | None = None,
    ) -> str:
        html = ""
        if subtype:
            html += (
                f'                <span class="message-badge subtype-badge">'
                f"{escape(subtype)}</span>\n"
            )
        if metadata_event_type:
            html += (
                f'                <span class="message-badge metadata-badge">'
                f"{escape(metadata_event_type)}</span>\n"
            )
        if subscribed:
            html += '                <span class="message-badge state-badge">subscribed</span>\n'
        if last_read is not None:
            html += (
                f'                <span class="message-badge state-badge">'
                f"last read {self.to_datetime(last_read)}</span>\n"
            )
        if upload:
            html += '                <span class="message-badge state-badge">upload</span>\n'
        if team_id:
            html += (
                f'                <span class="message-badge technical-badge">'
                f"team {escape(team_id)}</span>\n"
            )
        if client_msg_id:
            html += (
                f'                <span class="message-badge technical-badge">'
                f"client {escape(client_msg_id)}</span>\n"
            )
        return html

    @staticmethod
    def to_date(date: datetime) -> str:
        return date.strftime("%a, %d.%m.%Y")

    @staticmethod
    def to_time(date: datetime) -> str:
        return date.strftime("%H:%M:%S")

    @staticmethod
    def to_datetime(date: datetime) -> str:
        return date.strftime("%d.%m.%Y %H:%M:%S")

    def write_out_file(self, html: str):
        os.makedirs("out", exist_ok=True)
        file_name = f"out/{self.safe_output_name(self.slack_data.channel_name)}.html"
        with open(file_name, "w", encoding="utf-8") as html_file:
            html_file.write(html)
        print(f"{file_name} successfully written")
