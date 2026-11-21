# MicroLumin M6: what we measured (Fri Nov 20, 2026)

Everything here was probed on our own pair with `adb` and the Lucia app. It's what to build against when you
**don't have the glasses**. Serial numbers and MAC addresses are deliberately left out (this repo is public).
The vendor SDK kit is confidential and is **not** needed for any of this.

## System

| | |
|---|---|
| Model / OS | `XNM-Glass`, Android 9 (API 28), build `PPR1.180610.011`, `user/dev-keys` |
| SoC / RAM | Unisoc UWS6152 (W517 family): 1× Cortex-A75 + 3× Cortex-A55, ~1.9 GB RAM |
| Display | 640×480 @ 60 Hz, 160 dpi. Black = see-through. Launcher status bar covers the top ~40 px. |
| Browser engine | Android System WebView **74.0.3729** (Chrome 74). See `lens/AGENTS.md` for what that rules out. |
| Text-to-speech | **None installed.** The hub speaks (macOS `say`) and streams PCM 22.05 kHz mono to the app. |
| Default home app | `com.mlaixr.launcher/.MainActivity` (we replace it with Lucia; see `glasses-app/AGENTS.md`) |
| Screen timeout | 60 s by default. Lucia holds the screen on; `adb shell svc power stayon usb` keeps it awake on USB. |
| Time zone | Shipped as China (UTC+8). We set it to `America/New_York`; the lens uses the hub's clock regardless. |
| Link to laptop | USB + `adb reverse tcp:9100 tcp:9100` (no Wi-Fi needed), or Wi-Fi to the hub's IP |

## Inputs (temple touchpad = device `hyn_ts`)

Gestures arrive as instant key events (~7 ms down→up). **Tell them apart by key code, never by timing.**

| Gesture | Android keycode | scan | Lucia uses it for |
|---|---|---|---|
| Tap | 66 `ENTER` | 28 | ask (start listening) |
| Double tap | 142 `F12` (system then sends 4 `BACK`) | 88 | ask (any touch asks) |
| Long press | 141 `F11` | 87 | ask (the hint says "hold right side") |
| Swipe forward | 22 `DPAD_RIGHT` | 106 | ask (any touch asks) |
| Swipe back | 21 `DPAD_LEFT` | 105 | ask (any touch asks) |
| Swipe up / down | not supported (comes through as a tap) | | |
| **Glasses put on** | **301** from device `xnm_pannel` | 184 | greeting. This is the real wear detector; the Android off-body sensor never fired |
| Ring | **nothing received** (not paired / not present in our kit) | | |

Other input devices on the system (not seen in use): `gx8002` (F1–F6, F10, volume, next/prev, play/pause,
camera key, likely the voice-wake DSP or ring receiver), `xnm_pannel` (F13/F14), 8× `CapSense` channels,
headset keys.

## Camera

| | |
|---|---|
| Sensor | 1 camera, 4032×3024 (12 MP) array, 4.22 mm lens, hardware level LIMITED |
| Preview sizes | 1920×1080 … 640×480 … 176×144 (we use **640×480 NV21 → JPEG q70, ~40–48 KB**) |
| FPS ranges | 5–15, 5–20, … (we send ~1 fps to save battery) |
| Faces | `face_id` on the Mac matched Abhiram from the glasses camera at 0.74 (threshold 0.55) |

## Audio

| | |
|---|---|
| Mics | "Built-In Mic" + "Built-In Back Mic" (two). We record mono 16 kHz, `VOICE_RECOGNITION` source. |
| Speaker | One channel. Hub-streamed PCM16 22.05 kHz plays fine. |
| STT | mlx-whisper small.en on the Mac: 120–150 ms per question from the glasses mic, accurate at arm's length |

## Motion & environment sensors (at 50 Hz requested; ~63 Hz gyro observed)

| Sensor | Notes |
|---|---|
| Gyroscope (`gyro_sh5001`) | **Axes on the M6: x = yaw (head shake "no"), y = pitch (nod "yes"), z = roll (tilt).** Shake ≈ 256°/s RMS on x; nod ≈ 75°/s RMS on y; still ≈ < 6°/s. |
| Accelerometer (`acc_sh5001`) | ~48 Hz |
| Game rotation vector | ~95 Hz; good for head yaw ("which way am I looking") |
| Light (`acs5121`) | 5–300 lux indoors, ~1 Hz |
| Proximity | Mostly 5 (far), 0 briefly; not a reliable wear signal |
| Also present | magnetometer, pressure, step counter/detector, thermometer, Spreadtrum watch gestures (hand up/down, wrist scroll) |
| Off-body detect | Registers fine but **never reported**: use key 301 instead |

## Built-in MicroLumin apps (packages)

`com.mlaixr.launcher`, `.assistant.server`, `.camera`, `.capture.glass`, `.recorder`, `.translator.glass.host`,
`.prompter`, `.readerapp`, `.glass.navigation`, `.ring`, `.audiocare.glass.host`, `.connect`, `.livepush`,
`.mediacapture`, `.glass.dlna`, `.glass.ota`, `.tetris`, plus AOSP `com.android.camera2`.

## Working without the glasses

- **UI:** `sim/` (see `sim/AGENTS.md`).
- **Full pipeline:** `hub/tools/replay_glasses.py` acts as the glasses: speak any sentence, send any photo,
  press any gesture above, or replay a real recording:
  ```bash
  cd hub && uv run python tools/replay_glasses.py --say "Lucia, who is this?" --frame ../faces/sid/IMG_3167.jpg
  ```
- **Real recordings** from our glasses (mic, camera frames, IMU, keys) live in `hub/data/recordings/` on
  Shrikar's Mac: `still`, `right_temple`, `ring`, `nod`, `shake`, `voice_wearer`, `off_on`. They contain
  teammates' voices and faces, so they're shared privately, **never committed**. Record more with
  `tools/capture_session.py` when the glasses are back.
