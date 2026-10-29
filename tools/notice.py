"""One-off manual Telegram notice (outside the engine's alert rules). Sends tools/notice.txt either to the owner
only (`owner`) or to the owner and every subscriber (`all`). It reads the sealed subscriber list from the data
branch and writes nothing back."""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine import alerts  # noqa: E402


def main():
    to = (sys.argv[1] if len(sys.argv) > 1 else "owner").strip()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        sys.exit("no bot token")
    text = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "notice.txt"), encoding="utf-8").read().strip()
    state = json.loads(subprocess.check_output(["git", "show", "origin/data:state/alerts.json"]))
    owner = alerts._owner(state, token)
    chats = [owner] if owner else []
    if to == "all":
        chats += [c for c in alerts._subs(state, token) if c not in chats]
    elif to != "owner":
        sys.exit("target must be owner or all")
    if not chats:
        sys.exit("no chat to send to")
    sent = alerts.send_all(dict(state), token, chats, [text])
    print(f"sent {sent} of {len(chats)}")
    if not sent:
        sys.exit(1)


if __name__ == "__main__":
    main()
