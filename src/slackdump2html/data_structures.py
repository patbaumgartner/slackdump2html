from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


@dataclass
class SlackThreadMessage:
    user: str
    text: str
    date: datetime
    reactions: dict[str, int]
    avatar_url: str | None = None
    reaction_users: dict[str, list[str]] = field(default_factory=dict)
    edited: bool = False
    subtype: str | None = None
    metadata_event_type: str | None = None
    team_id: str | None = None
    client_msg_id: str | None = None


@dataclass
class SlackMessage:
    user: str
    text: str
    date: datetime
    reactions: dict[str, int]
    replies: list[SlackThreadMessage]
    avatar_url: str | None = None
    reaction_users: dict[str, list[str]] = field(default_factory=dict)
    edited: bool = False
    subtype: str | None = None
    metadata_event_type: str | None = None
    subscribed: bool = False
    last_read: datetime | None = None
    upload: bool = False
    team_id: str | None = None
    client_msg_id: str | None = None


class ChannelType(StrEnum):
    Channel = "#"
    Conversation = "@"
    Private = "🔒"
    Unknown = "?"


@dataclass
class SlackData:
    channel_type: ChannelType
    channel_name: str
    messages: list[SlackMessage]
    emojis: dict[str, str]

    def get_title_text(self) -> str:
        return self.channel_type.value + self.channel_name
