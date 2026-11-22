"""Append-only audit log of account changes, one JSON object per line."""
import getpass
import json
import os
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOG = Path(__file__).resolve().parent.parent / "data" / "audit.jsonl"


def log_path(path=None):
    return Path(path or os.environ.get("AUDIT_LOG") or DEFAULT_LOG)


def _actor():
    try:
        return getpass.getuser()
    except Exception:  # noqa: BLE001 - no login name in some containers
        return "unknown"


def record(action, target, reason, actor=None, path=None):
    if not reason or not reason.strip():
        raise ValueError("an audit reason is required")
    event = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "actor": actor or _actor(),
        "action": action,
        "target": target,
        "reason": reason.strip(),
    }
    p = log_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(event) + "\n")
    return event


def read(path=None, target=None, action=None):
    p = log_path(path)
    if not p.exists():
        return []
    events = []
    for n, line in enumerate(p.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"{p}:{n}: corrupt audit line") from e
        if (target is None or event.get("target") == target) and (action is None or event.get("action") == action):
            events.append(event)
    return events
