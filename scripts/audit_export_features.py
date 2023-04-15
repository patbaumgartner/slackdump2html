#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

SUPPORTED_TOP_LEVEL = {
    "type",
    "user",
    "text",
    "ts",
    "reactions",
    "slackdump_thread_replies",
    "blocks",
    "files",
    "attachments",
    "edited",
    "user_profile",
    "subtype",
    "metadata",
    "thread_ts",
    "reply_count",
    "latest_reply",
    "reply_users",
    "parent_user_id",
    "last_read",
    "subscribed",
    "upload",
    "team",
    "client_msg_id",
}

SUPPORTED_BLOCK_TYPES = {
    "actions",
    "context",
    "image",
    "rich_text",
    "section",
}

SUPPORTED_MESSAGE_SUBTYPES = {
    "channel_join",
    "thread_broadcast",
}


class FeatureAudit:
    def __init__(self) -> None:
        self.files_scanned = 0
        self.messages_scanned = 0
        self.replies_scanned = 0

        self.message_types: Counter[str] = Counter()
        self.message_subtypes: Counter[str] = Counter()
        self.block_types: Counter[str] = Counter()
        self.file_mimetypes: Counter[str] = Counter()
        self.unhandled_fields: Counter[str] = Counter()
        self.gap_signals: Counter[str] = Counter()

        self.examples: dict[str, str] = {}

    def _remember_example(self, key: str, location: str) -> None:
        self.examples.setdefault(key, location)

    def scan_export_file(self, export_file: Path) -> None:
        with export_file.open(encoding="utf-8") as fp:
            data = json.load(fp)

        self.files_scanned += 1

        if isinstance(data, list):
            messages = data
        elif isinstance(data, dict):
            messages = data.get("messages")
        else:
            messages = None

        if not isinstance(messages, list):
            self.gap_signals["invalid_messages_payload"] += 1
            self._remember_example("invalid_messages_payload", str(export_file))
            return

        for index, message in enumerate(messages):
            if not isinstance(message, dict):
                self.gap_signals["non_dict_message"] += 1
                self._remember_example("non_dict_message", f"{export_file}#{index}")
                continue
            self.scan_message(message, f"{export_file.name}#msg:{index}", is_reply=False)

    def scan_message(self, message: dict[str, Any], location: str, *, is_reply: bool) -> None:
        if is_reply:
            self.replies_scanned += 1
        else:
            self.messages_scanned += 1

        msg_type = str(message.get("type", "<missing>"))
        self.message_types[msg_type] += 1
        if msg_type != "message":
            self.gap_signals["non_message_type"] += 1
            self._remember_example("non_message_type", location)

        subtype = message.get("subtype")
        if isinstance(subtype, str) and subtype:
            self.message_subtypes[subtype] += 1
            if subtype not in SUPPORTED_MESSAGE_SUBTYPES:
                key = f"unsupported_subtype:{subtype}"
                self.gap_signals[key] += 1
                self._remember_example(key, location)

        if not self.has_renderable_content(message):
            self.gap_signals["message_without_text"] += 1
            self._remember_example("message_without_text", location)

        if "metadata" in message and not self.has_renderable_metadata(message):
            self.gap_signals["message_metadata_without_event_type"] += 1
            self._remember_example("message_metadata_without_event_type", location)

        for key in message.keys() - SUPPORTED_TOP_LEVEL:
            self.unhandled_fields[key] += 1

        blocks = message.get("blocks") or []
        if isinstance(blocks, list):
            for block in blocks:
                if not isinstance(block, dict):
                    self.gap_signals["non_dict_block"] += 1
                    self._remember_example("non_dict_block", location)
                    continue
                block_type = str(block.get("type", "<missing>"))
                self.block_types[block_type] += 1
                if block_type not in SUPPORTED_BLOCK_TYPES:
                    self.gap_signals[f"unsupported_block:{block_type}"] += 1
                    self._remember_example(f"unsupported_block:{block_type}", location)

        files = message.get("files") or []
        if isinstance(files, list):
            for file_obj in files:
                if not isinstance(file_obj, dict):
                    continue
                mimetype = str(file_obj.get("mimetype") or "<missing>")
                self.file_mimetypes[mimetype] += 1

        replies = message.get("slackdump_thread_replies") or []
        if isinstance(replies, list):
            for idx, reply in enumerate(replies):
                if isinstance(reply, dict):
                    self.scan_message(reply, f"{location}#reply:{idx}", is_reply=True)

    def has_renderable_content(self, message: dict[str, Any]) -> bool:
        text = message.get("text")
        has_text = isinstance(text, str) and bool(text.strip())
        if has_text:
            return True

        for key in ("blocks", "files", "attachments"):
            value = message.get(key)
            if isinstance(value, list) and len(value) > 0:
                return True

        return False

    def has_renderable_metadata(self, message: dict[str, Any]) -> bool:
        metadata = message.get("metadata")
        if not isinstance(metadata, dict):
            return False

        event_type = metadata.get("event_type")
        if isinstance(event_type, str) and bool(event_type.strip()):
            return True

        return bool(metadata)


def format_counter(counter: Counter[str], title: str, limit: int) -> list[str]:
    lines = [title]
    if not counter:
        lines.append("- none")
        return lines

    for key, value in counter.most_common(limit):
        lines.append(f"- {key}: {value}")
    return lines


def build_report(audit: FeatureAudit, *, top_n: int) -> str:
    lines: list[str] = []
    lines.append("# Slack Export Feature Audit")
    lines.append("")
    lines.append("## Scope")
    lines.append(f"- Files scanned: {audit.files_scanned}")
    lines.append(f"- Messages scanned: {audit.messages_scanned}")
    lines.append(f"- Replies scanned: {audit.replies_scanned}")
    lines.append("")

    lines.append("## Gap Signals (likely unsupported or partially supported)")
    if audit.gap_signals:
        for key, value in audit.gap_signals.most_common(top_n):
            example = audit.examples.get(key)
            if example:
                lines.append(f"- {key}: {value} (example: {example})")
            else:
                lines.append(f"- {key}: {value}")
    else:
        lines.append("- none")
    lines.append("")

    lines.extend(format_counter(audit.message_subtypes, "## Message Subtypes", top_n))
    lines.append("")
    lines.extend(format_counter(audit.block_types, "## Block Types", top_n))
    lines.append("")
    lines.extend(
        format_counter(audit.unhandled_fields, "## Unhandled Top-Level Message Fields", top_n)
    )
    lines.append("")
    lines.extend(format_counter(audit.file_mimetypes, "## File MIME Types", top_n))
    lines.append("")

    lines.append("## Next Step")
    lines.append(
        "- Implement missing rendering for the highest-frequency gap signals, "
        "then rerun this audit."
    )

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Slack exports for unsupported features.")
    parser.add_argument(
        "--export-dir",
        default="data/messages",
        help="Directory containing slackdump channel JSON exports.",
    )
    parser.add_argument(
        "--report",
        default="out/feature-audit.md",
        help="Path for generated markdown report.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="How many top entries to include per section.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    export_dir = Path(args.export_dir)

    if not export_dir.exists() or not export_dir.is_dir():
        raise SystemExit(f"Export directory not found: {export_dir}")

    export_files = sorted(export_dir.glob("*.json"))
    if not export_files:
        raise SystemExit(f"No JSON exports found in: {export_dir}")

    audit = FeatureAudit()
    for export_file in export_files:
        try:
            audit.scan_export_file(export_file)
        except json.JSONDecodeError:
            audit.gap_signals["invalid_json"] += 1
            audit._remember_example("invalid_json", str(export_file))

    report_text = build_report(audit, top_n=args.top_n)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")

    print(report_text)
    print(f"Report written to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
