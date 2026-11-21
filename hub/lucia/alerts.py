"""Caregiver alerts as real iMessages, sent by the Mac's Messages app (osascript).
Set LUCIA_DRY_RUN=1 to log instead of sending (tests, rehearsals)."""
from __future__ import annotations

import asyncio
import os
import subprocess
import time

SCRIPT = '''on run {phone, msg}
    tell application "Messages"
        set svc to 1st account whose service type = iMessage
        send msg to participant phone of svc
    end tell
end run'''


class Alerts:
    def __init__(self, cfg: dict, min_gap_s: int = 60):
        self.phone = cfg["caregiver"].get("phone", "")
        self.enabled = cfg.get("alerts", {}).get("imessage", False)
        self.min_gap = min_gap_s
        self.last = 0.0

    @property
    def dry(self) -> bool:
        return os.getenv("LUCIA_DRY_RUN") == "1" or not self.enabled or not self.phone or "000-0000" in self.phone

    def _send(self, text: str) -> str:
        if self.dry:
            print(f"[alert:dry-run] → {self.phone}: {text}")
            return "dry-run"
        r = subprocess.run(["osascript", "-e", SCRIPT, self.phone, text], capture_output=True, text=True, timeout=20)
        return "sent" if r.returncode == 0 else f"failed: {r.stderr.strip()[:200]}"

    async def send(self, text: str) -> str:
        now = time.time()
        if now - self.last < self.min_gap:
            return "rate-limited"
        self.last = now
        return await asyncio.get_running_loop().run_in_executor(None, self._send, text)
