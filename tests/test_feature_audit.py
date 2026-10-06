import json
from pathlib import Path
from runpy import run_path

FeatureAudit = run_path(
    str(Path(__file__).resolve().parents[1] / "scripts" / "audit_export_features.py")
)["FeatureAudit"]


def test_feature_audit_counts_messages_and_replies(tmp_path):
    export_file = tmp_path / "channel.json"
    export_file.write_text(
        json.dumps(
            {
                "messages": [
                    {
                        "type": "message",
                        "text": "parent",
                        "slackdump_thread_replies": [{"type": "message", "text": "reply"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    audit = FeatureAudit()
    audit.scan_export_file(export_file)

    assert audit.messages_scanned == 1
    assert audit.replies_scanned == 1
