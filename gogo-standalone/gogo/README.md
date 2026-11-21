# Gogo standalone server

No Lucia hub needed. One Python server that serves the lens, the dashboard and the simulator, keeps the care data, and runs Gogo's guided flow.

```
mockup\gogo\.venv\Scripts\python.exe mockup\gogo\main.py --port 9310
```

| Piece | What it does |
|---|---|
| `main.py` | FastAPI: `/ws/lens` (what to draw), `/ws/glasses` (keys, worn state in; voice out), the care API, static files |
| `flow.py` | the guided flow (splash, Hi I'm Gogo, weather, bag, freshen up, bathroom steps, wash hands, back to seat) and dashboard instructions |
| `tts.py` | speech for the glasses (Windows System.Speech, or macOS `say`) as 22.05 kHz mono PCM |

Glasses protocol (same as the teammates' app): text `hello {worn}`, `worn {value}`, `key {name, code}`; binary frames (mic, camera) are ignored; the server sends PCM voice as binary frames and `audio_stop`.
Tap (66), double tap (142), long press (141), swipes (21/22) = next. Key 301 (put on) starts the flow; taking them off puts the lens to sleep.

## Run on the real glasses (PC and glasses on the same Wi-Fi)
```
adb shell am start -n com.bb.lucia/.MainActivity --es hub ws://<PC-IP>:9310/ws/glasses --es lens http://<PC-IP>:9310/glasses/lens/index.html
```
(needs the teammates' glasses app installed; allow port 9310 through the Windows firewall.) Or over USB: `adb reverse tcp:9310 tcp:9310` and use `127.0.0.1`.

## Test without glasses
`POST /api/flow/start`, `/api/flow/next`, `/api/flow/stop`, `/api/flow/options {"auto":true,"voice":false}`.
