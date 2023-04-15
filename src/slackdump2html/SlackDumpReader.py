import base64
import json
import os
from datetime import datetime
from html import escape
from pathlib import Path

from slackdump2html.data_structures import (
    ChannelType,
    SlackData,
    SlackMessage,
    SlackThreadMessage,
)
from slackdump2html.SlackDataCleaner import SlackDataCleaner

EMOJI_PATH = "data/emojis/emojis/"


class SlackDumpReader:
    data_cleaner: SlackDataCleaner

    def __init__(self, data_cleaner: SlackDataCleaner):
        self.data_cleaner = data_cleaner

    def read(self, file_path: str) -> SlackData:
        with open(file_path, encoding="utf-8") as dump_file:
            dump_data = json.load(dump_file)

        file_name = Path(file_path).stem

        messages: list[SlackMessage] = []

        for message in dump_data["messages"]:
            if self.is_renderable_message(message):
                replies = self.read_replies(message)
                user_id = self.get_user(message)
                messages.append(
                    SlackMessage(
                        user=user_id,
                        text=self.get_message_content(message),
                        date=self.to_datetime(message["ts"]),
                        reactions=self.read_reactions(message),
                        replies=replies,
                        avatar_url=self.get_avatar_url(message, user_id),
                        reaction_users=self.read_reaction_users(message),
                        edited=isinstance(message.get("edited"), dict),
                        subtype=self.get_subtype_label(message),
                        metadata_event_type=self.get_metadata_event_type(message),
                        subscribed=bool(message.get("subscribed") is True),
                        last_read=self.get_optional_datetime(message.get("last_read")),
                        upload=bool(message.get("upload") is True),
                        team_id=self.get_optional_string(message.get("team")),
                        client_msg_id=self.get_optional_string(message.get("client_msg_id")),
                    )
                )

        channel_type, channel_name = self.get_channel_name(dump_data, file_name)
        slack_data = SlackData(
            channel_type=channel_type,
            channel_name=channel_name,
            messages=messages,
            emojis=self.read_emojis(),
        )

        return slack_data

    def get_channel_name(self, dump_data, file_name: str) -> tuple[ChannelType, str]:
        if file_name in self.data_cleaner.channel_map:
            return self.data_cleaner.channel_map[file_name]
        elif dump_data["name"] == "":
            return ChannelType.Unknown, file_name
        else:
            return ChannelType.Channel, dump_data["name"]

    def get_user(self, message: dict) -> str:
        if "user" in message:
            return message["user"]
        else:
            return "Unknown user"

    def is_renderable_message(self, message: dict) -> bool:
        if message.get("type") != "message":
            return False

        if message.get("hidden") is True:
            return False

        subtype = message.get("subtype")
        if not isinstance(subtype, str):
            return True

        return subtype not in {"bot_message", "message_changed", "message_deleted"}

    def get_subtype_label(self, message: dict) -> str | None:
        subtype = message.get("subtype")
        if isinstance(subtype, str) and subtype.strip():
            return subtype.replace("_", " ")
        return None

    def get_metadata_event_type(self, message: dict) -> str | None:
        metadata = message.get("metadata")
        if not isinstance(metadata, dict):
            return None

        event_type = metadata.get("event_type")
        if isinstance(event_type, str) and event_type.strip():
            return event_type.replace("_", " ")

        return "metadata"

    def get_message_content(self, message: dict) -> str:
        text = self.get_message_text(message)
        image_urls = self.get_shared_image_urls(message)
        file_markup = self.get_file_markup(message)
        attachment_markup = self.get_attachment_markup(message)

        blocks: list[str] = []
        if text:
            blocks.append(text)

        if image_urls:
            image_markup = "\n".join(
                (
                    '<figure class="shared-image">'
                    f'<img src="{escape(url, quote=True)}" '
                    'alt="Shared image" class="shared-image-img">'
                    f'<figcaption><a href="{escape(url, quote=True)}" '
                    'class="shared-image-link">Open image</a></figcaption>'
                    "</figure>"
                )
                for url in image_urls
            )
            blocks.append(image_markup)

        if file_markup:
            blocks.append(file_markup)

        if attachment_markup:
            blocks.append(attachment_markup)

        return "\n".join(blocks)

    def get_message_text(self, message: dict) -> str:
        text = message.get("text")
        if isinstance(text, str) and text.strip():
            return text

        blocks = message.get("blocks")
        if isinstance(blocks, list):
            extracted = self.extract_text_from_blocks(blocks).strip()
            if extracted:
                return extracted

        return ""

    def extract_text_from_blocks(self, blocks: list[dict]) -> str:
        lines: list[str] = []

        for block in blocks:
            if not isinstance(block, dict):
                continue

            block_type = block.get("type")

            if block_type == "section":
                text_obj = block.get("text")
                if isinstance(text_obj, dict):
                    section_text = text_obj.get("text")
                    if isinstance(section_text, str) and section_text.strip():
                        lines.append(section_text.strip())

                for field in block.get("fields") or []:
                    if not isinstance(field, dict):
                        continue
                    field_text = field.get("text")
                    if isinstance(field_text, str) and field_text.strip():
                        lines.append(field_text.strip())

            elif block_type in ("rich_text", "context", "actions"):
                extracted = self.extract_text_from_elements(block.get("elements") or [])
                if extracted:
                    lines.append(extracted)

        return "\n".join(line for line in lines if line)

    def extract_text_from_elements(self, elements: list[dict]) -> str:
        parts: list[str] = []

        for element in elements:
            if not isinstance(element, dict):
                continue

            element_type = element.get("type")

            if element_type in ("plain_text", "mrkdwn", "text"):
                text = element.get("text")
                if isinstance(text, str):
                    parts.append(text)

            elif element_type == "emoji":
                emoji_name = element.get("name")
                if isinstance(emoji_name, str) and emoji_name:
                    parts.append(f":{emoji_name}:")

            elif element_type == "link":
                url = element.get("url")
                link_text = element.get("text")
                if isinstance(url, str) and url:
                    if isinstance(link_text, str) and link_text:
                        parts.append(f"<{url}|{link_text}>")
                    else:
                        parts.append(f"<{url}>")

            elif element_type == "user":
                user_id = element.get("user_id")
                if isinstance(user_id, str) and user_id:
                    parts.append(f"<@{user_id}>")

            elif element_type == "broadcast":
                broadcast_range = element.get("range")
                if isinstance(broadcast_range, str) and broadcast_range:
                    parts.append(f"<!{broadcast_range}>")

            elif element_type == "channel":
                channel_id = element.get("channel_id")
                channel_name = element.get("name")
                if isinstance(channel_id, str) and channel_id:
                    if isinstance(channel_name, str) and channel_name:
                        parts.append(f"<#{channel_id}|{channel_name}>")
                    else:
                        parts.append(f"<#{channel_id}|{channel_id}>")

            elif element_type in (
                "rich_text_section",
                "rich_text_quote",
                "rich_text_preformatted",
            ):
                nested = self.extract_text_from_elements(element.get("elements") or [])
                if nested:
                    parts.append(nested)

            elif element_type == "rich_text_list":
                list_style = element.get("style")
                list_items: list[str] = []
                for item in element.get("elements") or []:
                    if not isinstance(item, dict):
                        continue
                    item_text = self.extract_text_from_elements(item.get("elements") or [])
                    if item_text:
                        prefix = "1." if list_style == "ordered" else "-"
                        list_items.append(f"{prefix} {item_text}")
                if list_items:
                    parts.append("\n".join(list_items))

            elif element_type == "button":
                text_obj = element.get("text")
                if isinstance(text_obj, dict):
                    button_text = text_obj.get("text")
                    if isinstance(button_text, str) and button_text:
                        parts.append(button_text)

        return "".join(parts)

    def get_file_markup(self, message: dict) -> str:
        entries: list[str] = []
        for file_obj in message.get("files") or []:
            if not isinstance(file_obj, dict):
                continue

            title = str(file_obj.get("title") or file_obj.get("name") or "File")
            pretty_type = str(file_obj.get("pretty_type") or file_obj.get("filetype") or "")
            size = file_obj.get("size")
            size_text = f"{int(size) // 1024} KB" if isinstance(size, int) else ""
            details = " \u2022 ".join(part for part in (pretty_type, size_text) if part)

            link = (
                file_obj.get("permalink")
                or file_obj.get("url_private_download")
                or file_obj.get("url_private")
            )

            normalized_media_link = self.normalize_media_url(link)
            if self.is_http_url(link):
                title_html = f'<a href="{escape(str(link), quote=True)}">{escape(title)}</a>'
            else:
                title_html = escape(title)

            detail_html = f'<p class="file-card-meta">{escape(details)}</p>' if details else ""
            preview_html = self.get_file_preview_markup(file_obj, normalized_media_link)
            entries.append(
                '<article class="file-card">'
                f'<p class="file-card-title">{title_html}</p>'
                f"{detail_html}"
                f"{preview_html}"
                "</article>"
            )

        return "\n".join(entries)

    def get_file_preview_markup(self, file_obj: dict, media_link: str | None) -> str:
        if not media_link:
            return ""

        mime_type = str(file_obj.get("mimetype") or "")
        safe_link = escape(media_link, quote=True)
        if mime_type.startswith("video/"):
            return (
                '<video controls preload="metadata" class="shared-video-player">'
                f'<source src="{safe_link}" type="{escape(mime_type, quote=True)}">'
                "Your browser does not support the video tag."
                "</video>"
            )

        if mime_type == "application/pdf":
            return (
                f'<a href="{safe_link}" class="shared-file-link">Open PDF</a>'
                f'<embed src="{safe_link}" type="application/pdf" class="shared-pdf-embed">'
            )

        return ""

    def get_attachment_markup(self, message: dict) -> str:
        entries: list[str] = []
        for attachment in message.get("attachments") or []:
            if not isinstance(attachment, dict):
                continue

            title = str(attachment.get("title") or attachment.get("fallback") or "Attachment")
            text = str(attachment.get("text") or "").strip()
            link = (
                attachment.get("title_link")
                or attachment.get("from_url")
                or attachment.get("original_url")
            )

            if self.is_http_url(link):
                title_html = f'<a href="{escape(str(link), quote=True)}">{escape(title)}</a>'
            else:
                title_html = escape(title)

            text_html = f'<p class="file-card-meta">{escape(text)}</p>' if text else ""
            entries.append(
                '<article class="file-card">'
                f'<p class="file-card-title">{title_html}</p>'
                f"{text_html}"
                "</article>"
            )

        return "\n".join(entries)

    def is_gif(self, message: dict) -> bool:
        blocks = message.get("blocks")
        if not blocks:
            return False
        return blocks[0]["type"] == "image" and str(blocks[0]["image_url"]).__contains__(
            "giphy.com"
        )

    def get_shared_image_urls(self, message: dict) -> list[str]:
        urls: list[str] = []

        for block in message.get("blocks") or []:
            if isinstance(block, dict) and block.get("type") == "image":
                image_url = block.get("image_url")
                if self.is_http_url(image_url):
                    urls.append(str(image_url))

        for file_obj in message.get("files") or []:
            if not isinstance(file_obj, dict):
                continue
            mime_type = str(file_obj.get("mimetype") or "")
            if not mime_type.startswith("image/"):
                continue
            image_url = (
                file_obj.get("url_private_download")
                or file_obj.get("url_private")
                or file_obj.get("permalink_public")
                or file_obj.get("permalink")
            )
            normalized = self.normalize_media_url(image_url)
            if normalized:
                urls.append(normalized)

        for attachment in message.get("attachments") or []:
            if not isinstance(attachment, dict):
                continue
            for key in ("image_url", "thumb_url"):
                image_url = attachment.get(key)
                if self.is_http_url(image_url):
                    urls.append(str(image_url))

        unique_urls = list(dict.fromkeys(urls))
        return unique_urls

    def is_http_url(self, value: object) -> bool:
        return isinstance(value, str) and value.startswith(("http://", "https://"))

    def normalize_media_url(self, value: object) -> str | None:
        if not isinstance(value, str):
            return None

        cleaned = value.strip()
        if not cleaned:
            return None

        if self.is_http_url(cleaned):
            return cleaned

        if cleaned.startswith("/"):
            return cleaned

        # Slack exports often store file paths relative to the export folder.
        return f"../data/messages/{cleaned.lstrip('./')}"

    def read_replies(self, message: dict) -> list[SlackThreadMessage]:
        replies: list[SlackThreadMessage] = []
        if "slackdump_thread_replies" in message:
            for reply in message["slackdump_thread_replies"]:
                if self.is_renderable_message(reply):
                    user_id = reply.get("user", "Unknown user")
                    replies.append(
                        SlackThreadMessage(
                            user=user_id,
                            text=self.get_message_content(reply),
                            date=self.to_datetime(reply["ts"]),
                            reactions=self.read_reactions(reply),
                            avatar_url=self.get_avatar_url(reply, user_id),
                            reaction_users=self.read_reaction_users(reply),
                            edited=isinstance(reply.get("edited"), dict),
                            subtype=self.get_subtype_label(reply),
                            metadata_event_type=self.get_metadata_event_type(reply),
                            team_id=self.get_optional_string(reply.get("team")),
                            client_msg_id=self.get_optional_string(reply.get("client_msg_id")),
                        )
                    )
        return replies

    def get_avatar_url(self, message: dict, user_id: str) -> str | None:
        avatar_url = self.data_cleaner.get_user_avatar(user_id)
        if avatar_url:
            return avatar_url
        profile = message.get("user_profile")
        if isinstance(profile, dict):
            return profile.get("image_72") or profile.get("image_48")
        return None

    def read_reactions(self, message: dict) -> dict[str, int]:
        reactions: dict[str, int] = {}
        if "reactions" in message:
            for reaction in message["reactions"]:
                reactions[reaction["name"]] = reaction["count"]
        return reactions

    def read_reaction_users(self, message: dict) -> dict[str, list[str]]:
        reaction_users: dict[str, list[str]] = {}
        for reaction in message.get("reactions") or []:
            if not isinstance(reaction, dict):
                continue
            name = reaction.get("name")
            users = reaction.get("users")
            if not isinstance(name, str) or not isinstance(users, list):
                continue
            reaction_users[name] = [str(user) for user in users if isinstance(user, str)]
        return reaction_users

    def read_emojis(self) -> dict[str, str]:
        if not Path("data/emojis/index.json").exists():
            return {}

        with open("data/emojis/index.json", encoding="utf-8") as emoji_file:
            emoji_data = json.load(emoji_file)

        emojis: dict[str, str] = {}
        for emoji in emoji_data.items():
            if not emoji[1].startswith("alias:"):
                emoji_file_name = self.get_emoji_file_name(emoji[0])
                if emoji_file_name.startswith("<none>"):
                    continue

                with open(emoji_file_name, "rb") as image:
                    image_data = image.read()
                    image_type = self.get_image_type(image_data)
                    base64_data = base64.encodebytes(image_data).decode("utf-8").replace("\n", "")
                    emojis[emoji[0]] = image_type + ";base64," + base64_data

        for emoji in emoji_data.items():
            if emoji[1].startswith("alias:") and emoji[1][6:] in emojis:
                emojis[emoji[0]] = emojis[emoji[1][6:]]

        return emojis

    def get_emoji_file_name(self, emoji_name: str) -> str:
        if os.path.exists(EMOJI_PATH + emoji_name + ".gif"):
            return EMOJI_PATH + emoji_name + ".gif"
        elif os.path.exists(EMOJI_PATH + emoji_name + ".jpeg"):
            return EMOJI_PATH + emoji_name + ".jpeg"
        elif os.path.exists(EMOJI_PATH + emoji_name + ".jpg"):
            return EMOJI_PATH + emoji_name + ".jpg"
        elif os.path.exists(EMOJI_PATH + emoji_name + ".png"):
            return EMOJI_PATH + emoji_name + ".png"
        else:
            return "<none>" + emoji_name

    def get_image_type(self, image_data: bytes) -> str:
        if image_data.startswith(bytes("GIF", "utf-8")):
            return "image/gif"
        else:
            # TODO support other image types. Not urgent - it works like that,
            # but is technically wrong.
            return "image/png"

    @staticmethod
    def to_datetime(timestamp: str) -> datetime:
        return datetime.fromtimestamp(float(timestamp))

    def get_optional_datetime(self, timestamp: object) -> datetime | None:
        if isinstance(timestamp, str) and timestamp.strip():
            return self.to_datetime(timestamp)
        return None

    def get_optional_string(self, value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None
