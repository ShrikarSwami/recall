"""Drive a real Chromium 74 (the engine in the M6 glasses' web view) from Python, for testing the lens.

    from chrome74 import C74
    b = C74(640, 480); b.goto("http://localhost:9300/..."); b.shot("out.png"); print(b.logs); b.close()
"""
import base64
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request

from websocket import create_connection

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = os.path.abspath(os.path.join(HERE, "..", "..", "chromium74", "app", "chrome-win", "chrome.exe"))


class C74:
    def __init__(self, w=640, h=480, port=9333, args=None):
        self.dir = tempfile.mkdtemp(prefix="c74-")
        a = [CHROME, "--headless", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--remote-debugging-port=%d" % port,
             "--user-data-dir=" + self.dir, "--window-size=%d,%d" % (w, h), "--force-device-scale-factor=1", "--hide-scrollbars",
             "--use-fake-ui-for-media-stream", "about:blank"] + (args or [])
        self.p = subprocess.Popen(a, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        url = None
        for _ in range(60):
            try:
                tabs = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json" % port, timeout=1))
                pages = [t for t in tabs if t.get("type") == "page"]
                if pages:
                    url = pages[0]["webSocketDebuggerUrl"]
                    break
            except Exception:
                time.sleep(0.25)
        if not url:
            self.close()
            raise RuntimeError("Chromium 74 did not start")
        self.ws = create_connection(url, timeout=30)
        self.n = 0
        self.logs = []
        for m in ("Page.enable", "Runtime.enable", "Log.enable"):
            self.send(m)
        self.size(w, h)

    def send(self, method, params=None):
        self.n += 1
        mid = self.n
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                return msg.get("result", {})
            self._event(msg)

    def _event(self, msg):
        m = msg.get("method")
        p = msg.get("params", {})
        if m == "Runtime.exceptionThrown":
            d = p["exceptionDetails"]
            self.logs.append("EXCEPTION: " + (d.get("exception", {}).get("description") or d.get("text", "")))
        elif m == "Runtime.consoleAPICalled" and p.get("type") in ("error", "warning"):
            self.logs.append("console.%s: %s" % (p["type"], " ".join(str(a.get("value", a.get("description", ""))) for a in p.get("args", []))))
        elif m == "Log.entryAdded" and p["entry"].get("level") in ("error", "warning"):
            self.logs.append("%s: %s" % (p["entry"]["level"], p["entry"]["text"]))

    def pump(self, seconds):
        end = time.time() + seconds
        self.ws.settimeout(0.2)
        while time.time() < end:
            try:
                self._event(json.loads(self.ws.recv()))
            except Exception:
                pass
        self.ws.settimeout(30)

    def size(self, w, h):
        self.send("Emulation.setDeviceMetricsOverride", {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": False})

    def goto(self, url, wait=1.5):
        self.send("Page.navigate", {"url": url})
        self.pump(wait)

    def eval(self, expr):
        r = self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
        if "exceptionDetails" in r:
            return "JS-ERROR: " + str(r["exceptionDetails"].get("exception", {}).get("description", r["exceptionDetails"].get("text")))
        return r.get("result", {}).get("value")

    def shot(self, path, clip=None):
        p = {"format": "png"}
        if clip:
            p["clip"] = dict(clip, scale=1)
        data = self.send("Page.captureScreenshot", p)["data"]
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass
        try:
            self.p.kill()
            self.p.wait(timeout=5)
        except Exception:
            pass
        shutil.rmtree(self.dir, ignore_errors=True)


if __name__ == "__main__":
    import sys
    b = C74(1024, 768)
    try:
        b.goto(sys.argv[1], 2.5)
        print("UA:", b.eval("navigator.userAgent"))
        b.shot(sys.argv[2])
        print("logs:", b.logs)
    finally:
        b.close()
