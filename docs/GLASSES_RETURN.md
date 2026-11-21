# Glasses are back: 15-minute re-onboarding checklist (Sat morning)

Goal: the full demo running **with no cable** (glasses on Wi-Fi → hub on the Mac). USB stays as the fallback.
Hardware facts: `docs/HARDWARE.md`. Build/install details: `glasses-app/AGENTS.md`.

## 0. Before they arrive (laptop only)

- [ ] `git pull` in `~/Projects/recall`; `cd hub && uv run pytest -q` passes.
- [ ] Hub running on 9100. For rehearsals keep `LUCIA_DRY_RUN=1`; **for the real demo start it without it** (real iMessage).
- [ ] APK built: `cd glasses-app && JAVA_HOME=/opt/homebrew/opt/openjdk@17 ./gradlew assembleDebug`.
- [ ] Decide the network (see §3) and note the Mac's IP on it: `ipconfig getifaddr en0`.

## 1. Same pair? (2 min, USB)

- [ ] `adb devices` shows it. If not: Developer Mode in the MLDemo iOS app → Glasses → Developer, replug USB.
- [ ] `adb shell getprop ro.product.model` → `XNM-Glass`. If it's a **different pair**, also do the "new pair" box below.
- [ ] `adb shell pm list packages | grep com.bb.lucia` → Go-go is still installed (and is still the home app).

> **New pair:** install the APK, grant CAMERA + RECORD_AUDIO, set the home activity, set the time zone
> (`adb shell setprop persist.sys.timezone America/New_York`), all from `glasses-app/AGENTS.md`.

## 2. Install the latest app (1 min, USB)

```bash
cd glasses-app
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb reverse tcp:9100 tcp:9100
```

## 3. Cut the cable: Wi-Fi to the hub (5 min) — the risky part, do it first

The glasses and the Mac must be on the **same network and able to reach each other**. Venue Wi-Fi often blocks
device-to-device traffic, so test it:

1. Turn the glasses' Wi-Fi on and join a network: MLDemo app → Glasses → Wi-Fi (or `adb shell svc wifi enable`
   then pick the network in the app). Best options, in order:
   - **Phone hotspot** (iPhone Personal Hotspot): both the Mac and the glasses join it. Most reliable; no venue
     client isolation. Keep the phone plugged in.
   - Venue Wi-Fi, if step 3 below works.
2. Find the glasses' IP: `adb shell ip addr show wlan0 | grep inet`.
3. From the glasses, reach the Mac: `adb shell ping -c 2 <mac-ip>` and `adb shell curl -s http://<mac-ip>:9100/api/state`
   (if `curl` is missing, skip; step 4 proves it).
4. Point the app at **Wi-Fi first, USB as fallback** (it rotates between them every 2 s until one answers):
   ```bash
   adb shell am start -n com.bb.lucia/.MainActivity \
     --es hub "ws://<mac-ip>:9100/ws/glasses,ws://127.0.0.1:9100/ws/glasses"
   ```
5. `adb logcat -s Go-go | grep -i "connected\|trying hub"` → `connected ws://<mac-ip>:9100/ws/glasses`.
6. **Unplug USB.** The lens should keep its hint and answer "Go-go, what day is it?". 
7. Screen: on USB we used `svc power stayon usb`; off USB, Go-go keeps the screen on itself. Check it stays on
   for 3 min. Note battery % now and after each rehearsal (unmeasured so far).

If Wi-Fi can't work in time: plug back in. USB is the fallback and the app switches back automatically.

> "Fully native" (everything on the glasses, no Mac) isn't realistic by 2 PM: the M6 has no TTS engine, 1.9 GB RAM
> and a phone-class CPU. Pitch it as: glasses + the family's own phone/laptop at home, no cloud. Wireless is the win.

## 4. Re-check faces under venue light (3 min)

- [ ] Each teammate stands ~1 m in front: hub log shows `seen person=<id> score=…` (≥ 0.55).
- [ ] Missing or weak? Take 3 photos at the venue (front, slight left, slight right) into `faces/<id>/`,
      then `cd hub && uv run python -m lucia.faces` and `curl -XPOST localhost:9100/api/reload`.
- [ ] Isha: photos still needed.

## 5. Inputs (1 min)

- [ ] Tap and **hold** the right temple → "Listening…" (any touch asks).
- [ ] Put the glasses on → greeting (key 301).
- [ ] Ask "Who is Abhiram?" → "Want to hear more?" → **nod** → next fact; **shake** → "Okay." (first time on real
      glasses; gyro thresholds are from our recordings, tune `hub/lucia/gestures.py` if needed).

## 6. Three rehearsals with `docs/DEMO.md` (rest of the time)

- [ ] Run 1 in dry-run. Run 2 and 3 with **real iMessage** (hub without `LUCIA_DRY_RUN`); the phone shows the text.
- [ ] Time each run (target ≤ 3:00). Note anything misheard → add `also:` phrasings to `knowledge/`.
- [ ] Before judging: `rm hub/data/events.jsonl` so the caregiver page starts clean (optional).
