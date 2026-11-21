# glasses-app: the Lucia app that runs on the M6

A plain Android 9 app (no MicroLumin SDK needed). It shows a black, see-through UI with
`Say "Lucia" to ask` pinned bottom-left and the time bottom-right (the launcher's status bar covers the top ~40 px). It streams the mic (16 kHz PCM) and
~1 fps camera JPEGs to the hub over a WebSocket, sends touchpad/ring presses, and plays the answers.
Protocol: see the comment at the top of `MainActivity.kt`.

## Build and install

Needs JDK 17 and the Android SDK (`local.properties` → `sdk.dir=...`).

```bash
JAVA_HOME=/opt/homebrew/opt/openjdk@17 ./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell pm grant com.bb.lucia android.permission.CAMERA
adb shell pm grant com.bb.lucia android.permission.RECORD_AUDIO
adb reverse tcp:9100 tcp:9100      # USB link to the Mac, no Wi-Fi needed
adb shell am start -n com.bb.lucia/.MainActivity --es hub ws://127.0.0.1:9100/ws/glasses
adb logcat -s Lucia        # key codes, camera sizes, mic/tts status
```

Glasses must be in Developer Mode first (MLDemo iOS app → Glasses → Developer), then replug USB.
To test the hardware without the real hub: `cd ../hub && uv run python probe.py`.
