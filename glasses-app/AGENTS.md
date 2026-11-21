# glasses-app/: the Android app on the M6 (Kotlin, Android 9 / API 28)

A thin client. It:
- streams the **mic** (16 kHz PCM) and **camera** (~1 fps 640×480 JPEG) to the hub over `ws://…:9100/ws/glasses`;
- sends **touchpad/ring** presses as key codes (66 ENTER = tap = "ask"; 21/22 swipes; 142+4 another gesture);
- sends the **off-body sensor** (glasses put on → greeting);
- plays the hub's **voice** (PCM 22.05 kHz). The glasses have no TTS engine;
- shows the **web lens** (`lens/`, loaded from `http://<hub>/lens/`) full-screen in a WebView. UI changes go in
  `lens/`, not here.
- is registered as the **home app**, so it's the only thing the wearer ever sees, and BACK can't close it.

## Build, install, run (glasses on USB, Developer Mode on)

```bash
JAVA_HOME=/opt/homebrew/opt/openjdk@17 ./gradlew assembleDebug        # needs Android SDK in local.properties
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell pm grant com.bb.lucia android.permission.CAMERA
adb shell pm grant com.bb.lucia android.permission.RECORD_AUDIO
adb reverse tcp:9100 tcp:9100                                          # USB link to the hub
adb shell am start -n com.bb.lucia/.MainActivity --es hub ws://127.0.0.1:9100/ws/glasses
adb shell cmd package set-home-activity com.bb.lucia/.MainActivity      # make Lucia the home app
adb logcat -s Lucia                                                     # key codes, camera, lens console
```

- Point the lens at a teammate's dev server: `--es lens http://<their-ip>:9200/lens/index.html?ws=ws://<hub>:9100/ws/lens`
- Restore MicroLumin's launcher: `adb shell cmd package set-home-activity com.mlaixr.launcher/.MainActivity`
- Inspect the lens WebView: `chrome://inspect` on the laptop while USB is connected.

Measured hardware facts are in `docs/SPEC.md` §6a. The MicroLumin SDK isn't needed and **must never be
committed** (confidential).
