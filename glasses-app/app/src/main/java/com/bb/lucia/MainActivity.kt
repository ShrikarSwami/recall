package com.bb.lucia

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Context
import android.graphics.Color
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.SurfaceTexture
import android.graphics.Typeface
import android.graphics.YuvImage
import android.hardware.Camera
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import android.util.Log
import android.view.Gravity
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import okio.ByteString.Companion.toByteString
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit

/**
 * Lucia glasses app: a thin, dumb terminal. All intelligence lives in hub/.
 *
 *  glasses → hub   text  {"type":"hello", caps...} | {"type":"key","name":"tap|double_tap|long_press|..","code":n}
 *                  binary 0x01 + PCM16 mono 16 kHz   (mic, ~100 ms chunks, always streaming)
 *                  binary 0x02 + JPEG 640x480         (camera, ~1 fps, and on request)
 *  hub → glasses   text  {"type":"config","hint":..} | {"type":"card","title":..,"lines":[..],"ttl_ms":n}
 *                        {"type":"state","value":"idle|listening|thinking"} | {"type":"say","text":..}
 *                        {"type":"snap"}  (send a frame now)
 *                  binary PCM16 mono 22050 Hz         (answer audio, played as it arrives)
 *
 * Configure:  adb shell am start -n com.bb.lucia/.MainActivity --es hub ws://<mac-ip>:9100/ws/glasses
 *             (comma-separate several to fall back, e.g. "ws://<mac-ip>:9100/ws/glasses,ws://127.0.0.1:9100/ws/glasses")
 * Logs:       adb logcat -s Lucia
 */
class MainActivity : Activity(), TextToSpeech.OnInitListener, android.hardware.SensorEventListener {
    private val ui = Handler(Looper.getMainLooper())
    private lateinit var hint: TextView
    private lateinit var clock: TextView
    private lateinit var status: TextView
    private lateinit var title: TextView
    private lateinit var body: TextView

    private val http = OkHttpClient.Builder().pingInterval(10, TimeUnit.SECONDS).build()
    private var ws: WebSocket? = null
    private var connected = false
    private lateinit var hubUrl: String
    private var hubs: List<String> = emptyList()
    private var hubIdx = 0
    private val USB_HUB = "ws://127.0.0.1:9100/ws/glasses"

    private var camera: Camera? = null
    private var lastFrameMs = 0L
    private var frameEveryMs = 1000L
    private var snapRequested = false
    private val camTexture = SurfaceTexture(10)

    private var recorder: AudioRecord? = null
    @Volatile private var micOn = true
    private var player: AudioTrack? = null
    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var clearCard: Runnable? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON or WindowManager.LayoutParams.FLAG_FULLSCREEN)
        val prefs = getSharedPreferences("lucia", Context.MODE_PRIVATE)
        intent.getStringExtra("hub")?.let { prefs.edit().putString("hub", it).apply() }
        intent.getStringExtra("lens")?.let { prefs.edit().putString("lens", it).apply() }  // e.g. a teammate's dev server
        // One or more hub URLs, comma-separated, tried in turn until one answers: e.g. the Mac over Wi-Fi first,
        // then USB (adb reverse) as a fallback, so the cable can come out without reconfiguring anything.
        hubs = prefs.getString("hub", USB_HUB)!!.split(",").map { it.trim() }.filter { it.isNotEmpty() }
            .ifEmpty { listOf(USB_HUB) }
        hubUrl = hubs[0]
        buildUi()
        tts = TextToSpeech(this, this)
        connect()
        startMic()
        ui.post(tick)
        // Off-body sensor: tells the hub when the glasses go on/off a face (auto-greet).
        (getSystemService(Context.SENSOR_SERVICE) as android.hardware.SensorManager).let { sm ->
            sm.getDefaultSensor(android.hardware.Sensor.TYPE_LOW_LATENCY_OFFBODY_DETECT, true)?.let {
                sm.registerListener(this, it, android.hardware.SensorManager.SENSOR_DELAY_NORMAL)
                log("offbody sensor registered")
            }
        }
        log("start hub=$hubUrl model=${android.os.Build.MODEL} sdk=${android.os.Build.VERSION.SDK_INT}")
    }

    // ------------------------------------------------------------------ UI (black = transparent)
    private fun tv(size: Float, bold: Boolean = false) = TextView(this).apply {
        setTextColor(Color.rgb(0, 255, 80)); textSize = size
        typeface = Typeface.create("sans-serif", if (bold) Typeface.BOLD else Typeface.NORMAL)
    }

    private fun buildUi() {
        val root = FrameLayout(this).apply { setBackgroundColor(Color.BLACK) }
        hint = tv(16f).apply { text = "Say “Lucia” or hold right side" }
        clock = tv(16f)
        status = tv(14f).apply { alpha = 0.8f }
        title = tv(30f, true)
        body = tv(22f).apply { maxLines = 3 }
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER_VERTICAL
            setPadding(56, 0, 56, 0); addView(title); addView(body)
        }
        root.addView(card, FrameLayout.LayoutParams(-1, -1))
        // The M6 launcher draws its own status bar (clock, BT, battery) over the top ~40 px,
        // so our pinned hint lives in the bottom-left corner where nothing covers it.
        root.addView(hint, FrameLayout.LayoutParams(-2, -2, Gravity.BOTTOM or Gravity.START).apply { setMargins(24, 0, 0, 18) })
        root.addView(clock, FrameLayout.LayoutParams(-2, -2, Gravity.BOTTOM or Gravity.END).apply { setMargins(0, 0, 24, 18) })
        root.addView(status, FrameLayout.LayoutParams(-2, -2, Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL).apply { setMargins(0, 0, 0, 52) })
        // The real UI is the web lens (lens/ in the repo, served by the hub at /lens/), owned by the
        // frontend devs. The native views above are only a fallback while the hub is unreachable.
        root.addView(buildLens(), FrameLayout.LayoutParams(-1, -1))
        setContentView(root)
        @Suppress("DEPRECATION")
        root.systemUiVisibility = (android.view.View.SYSTEM_UI_FLAG_FULLSCREEN or android.view.View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
            or android.view.View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or android.view.View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN)
        root.isFocusable = true; root.isFocusableInTouchMode = true; root.requestFocus()
    }

    private lateinit var lens: android.webkit.WebView
    private var lensOk = false
    private var lensHost = ""

    private fun lensUrl(): String {
        val override = getSharedPreferences("lucia", Context.MODE_PRIVATE).getString("lens", null)
        if (override != null) return override
        // ws://host:port/ws/glasses -> http://host:port/lens/
        return hubUrl.replaceFirst("ws://", "http://").replaceFirst("wss://", "https://").substringBefore("/ws/") + "/lens/"
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun buildLens(): android.webkit.WebView {
        lens = android.webkit.WebView(this).apply {
            setBackgroundColor(Color.BLACK)
            visibility = android.view.View.INVISIBLE
            isFocusable = false            // keys stay with the activity -> hub
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.cacheMode = android.webkit.WebSettings.LOAD_NO_CACHE
            webViewClient = object : android.webkit.WebViewClient() {
                override fun onPageFinished(view: android.webkit.WebView, url: String) {
                    if (lensOk) view.visibility = android.view.View.VISIBLE
                    log("lens loaded ok=$lensOk $url")
                }
                override fun onPageStarted(view: android.webkit.WebView, url: String, favicon: android.graphics.Bitmap?) { lensOk = true }
                @Suppress("DEPRECATION")
                override fun onReceivedError(view: android.webkit.WebView, code: Int, desc: String?, failing: String?) {
                    lensOk = false; view.visibility = android.view.View.INVISIBLE
                    log("lens error $code $desc; retrying")
                    ui.postDelayed({ view.loadUrl(lensUrl()) }, 3000)
                }
            }
            webChromeClient = object : android.webkit.WebChromeClient() {
                override fun onConsoleMessage(m: android.webkit.ConsoleMessage): Boolean {
                    log("lens console: ${m.message()} (${m.sourceId()}:${m.lineNumber()})"); return true
                }
            }
        }
        android.webkit.WebView.setWebContentsDebuggingEnabled(true)  // chrome://inspect from the laptop
        lensHost = hubUrl
        lens.loadUrl(lensUrl())
        return lens
    }

    private val tick = object : Runnable {
        override fun run() {
            clock.text = SimpleDateFormat("h:mm", Locale.US).format(Date())
            if (!connected) status.text = "connecting…"
            ui.postDelayed(this, 5000)
        }
    }

    private fun showCard(t: String, lines: List<String>, ttlMs: Long) = ui.post {
        title.text = t; body.text = lines.joinToString("\n")
        clearCard?.let { ui.removeCallbacks(it) }
        clearCard = Runnable { title.text = ""; body.text = "" }.also { ui.postDelayed(it, ttlMs) }
    }

    // ------------------------------------------------------------------ hub link
    private fun connect() {
        ws = http.newWebSocket(Request.Builder().url(hubUrl).build(), object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                connected = true
                ui.post { status.text = "" }
                val caps = JSONObject().put("type", "hello").put("model", android.os.Build.MODEL)
                    .put("sdk", android.os.Build.VERSION.SDK_INT).put("tts", ttsReady)
                    .put("cameras", Camera.getNumberOfCameras()).put("worn", worn ?: JSONObject.NULL)
                webSocket.send(caps.toString())
                log("connected $hubUrl")
                ui.post { if (lensHost != hubUrl) { lensHost = hubUrl; lens.loadUrl(lensUrl()) } }
                ui.post { openCamera() }
            }

            override fun onMessage(webSocket: WebSocket, text: String) = handle(JSONObject(text))

            override fun onMessage(webSocket: WebSocket, bytes: ByteString) = play(bytes.toByteArray())

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                connected = false; log("ws failure ${t.message}"); retry()
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) { connected = false; retry() }
        })
    }

    private fun retry() = ui.postDelayed({
        if (hubs.size > 1) {                 // try the next hub address (Wi-Fi <-> USB)
            hubIdx = (hubIdx + 1) % hubs.size
            hubUrl = hubs[hubIdx]
            log("trying hub $hubUrl")
        }
        connect()
    }, 2000)

    private fun handle(m: JSONObject) {
        when (m.optString("type")) {
            "config" -> ui.post {
                hint.text = m.optString("hint", hint.text.toString())
                frameEveryMs = m.optLong("frameEveryMs", frameEveryMs)
            }
            "card" -> {
                val arr = m.optJSONArray("lines")
                val lines = (0 until (arr?.length() ?: 0)).map { arr!!.getString(it) }
                showCard(m.optString("title"), lines, m.optLong("ttl_ms", 8000))
            }
            "state" -> ui.post {
                status.text = when (m.optString("value")) {
                    "listening" -> "● listening"; "thinking" -> "…"; else -> ""
                }
            }
            "audio_stop" -> {
                player?.pause()
                player?.flush()
                player?.play()
                tts?.stop()
            }
            "clear" -> ui.post {
                clearCard?.let { ui.removeCallbacks(it) }
                title.text = ""; body.text = ""; status.text = ""
            }
            "say" -> if (ttsReady) tts?.speak(m.optString("text"), TextToSpeech.QUEUE_FLUSH, null, "lucia")
            "snap" -> snapRequested = true
            "mic" -> micOn = m.optBoolean("on", true)
            "imu" -> ui.post { setImu(m.optBoolean("on", false)) }
        }
    }

    private fun sendBinary(tag: Byte, data: ByteArray, len: Int = data.size) {
        if (!connected) return
        val buf = ByteArray(len + 1); buf[0] = tag; System.arraycopy(data, 0, buf, 1, len)
        ws?.send(buf.toByteString())
    }

    // ------------------------------------------------------------------ mic → hub
    @SuppressLint("MissingPermission")
    private fun startMic() {
        Thread {
            val rate = 16000
            val min = AudioRecord.getMinBufferSize(rate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
            try {
                recorder = AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION, rate,
                    AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, maxOf(min, 6400))
                recorder!!.startRecording()
                log("mic started state=${recorder!!.recordingState}")
            } catch (e: Exception) { log("mic failed $e"); return@Thread }
            val chunk = ByteArray(3200) // 100 ms
            while (true) {
                val n = recorder!!.read(chunk, 0, chunk.size)
                if (n > 0 && micOn) sendBinary(1, chunk, n)
            }
        }.start()
    }

    // ------------------------------------------------------------------ camera → hub
    private fun openCamera() {
        if (camera != null) return
        try {
            camera = Camera.open(0).apply {
                val p = parameters
                val size = p.supportedPreviewSizes.minByOrNull { Math.abs(it.width - 640) + Math.abs(it.height - 480) }!!
                p.setPreviewSize(size.width, size.height)
                p.previewFormat = ImageFormat.NV21
                parameters = p
                log("camera preview ${size.width}x${size.height}; sizes=" + p.supportedPreviewSizes.joinToString { "${it.width}x${it.height}" })
                setPreviewTexture(camTexture)
                setPreviewCallback { data, cam -> onFrame(data, cam) }
                startPreview()
            }
        } catch (e: Exception) {
            log("camera failed $e; retrying in 3 s")
            camera = null
            ui.postDelayed({ openCamera() }, 3000)   // e.g. a previous instance still holds the camera
        }
    }

    private fun onFrame(nv21: ByteArray, cam: Camera) {
        val now = System.currentTimeMillis()
        if (!snapRequested && now - lastFrameMs < frameEveryMs) return
        lastFrameMs = now; snapRequested = false
        val s = cam.parameters.previewSize
        val out = ByteArrayOutputStream()
        YuvImage(nv21, ImageFormat.NV21, s.width, s.height, null).compressToJpeg(Rect(0, 0, s.width, s.height), 70, out)
        sendBinary(2, out.toByteArray())
    }

    // ------------------------------------------------------------------ audio out
    private fun play(pcm: ByteArray) {
        if (player == null) {
            val rate = 22050
            player = AudioTrack(AudioManager.STREAM_MUSIC, rate, AudioFormat.CHANNEL_OUT_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                maxOf(AudioTrack.getMinBufferSize(rate, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT), 8820),
                AudioTrack.MODE_STREAM).apply { play() }
        }
        player!!.write(pcm, 0, pcm.size)
    }

    override fun onInit(status: Int) {
        ttsReady = status == TextToSpeech.SUCCESS && tts?.setLanguage(Locale.US)?.let { it >= 0 } == true
        log("tts ready=$ttsReady engine=${tts?.defaultEngine}")
    }

    // ------------------------------------------------------------------ touchpad / ring
    // The M6 firmware turns temple-touchpad gestures (device "hyn_ts") into instant key events
    // (~7 ms down→up), so gestures are told apart by key code, not timing. Measured Fri Nov 20 (docs/HARDWARE.md):
    //   66 ENTER = tap · 142 F12 = double tap (followed by a system BACK) · 141 F11 = long press
    //   22 DPAD_RIGHT = swipe forward · 21 DPAD_LEFT = swipe back · swipe up/down not supported
    //   301 from "xnm_pannel" = glasses put on (the real wear detector; the off-body sensor never fires)
    // BACK is swallowed so a gesture can never close Lucia (every session = brand-new user).
    private fun gestureName(code: Int) = when (code) {
        KeyEvent.KEYCODE_ENTER, KeyEvent.KEYCODE_DPAD_CENTER -> "tap"
        KeyEvent.KEYCODE_F12 -> "double_tap"
        KeyEvent.KEYCODE_F11 -> "long_press"
        KeyEvent.KEYCODE_DPAD_RIGHT -> "swipe_forward"
        KeyEvent.KEYCODE_DPAD_LEFT -> "swipe_back"
        KeyEvent.KEYCODE_BACK -> "back"
        301 -> "worn"
        else -> "key_$code"
    }

    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        log("key code=${event.keyCode} (${KeyEvent.keyCodeToString(event.keyCode)}) action=${event.action} repeat=${event.repeatCount}")
        if (event.keyCode == KeyEvent.KEYCODE_VOLUME_UP || event.keyCode == KeyEvent.KEYCODE_VOLUME_DOWN) return super.dispatchKeyEvent(event)
        if (event.action == KeyEvent.ACTION_UP) {
            if (event.keyCode == 301) ws?.send(JSONObject().put("type", "worn").put("value", true).toString())
            sendKey(gestureName(event.keyCode), event.keyCode, event.scanCode, event.device?.name ?: "?")
        }
        return true
    }

    override fun onGenericMotionEvent(event: MotionEvent): Boolean {
        log("motion src=${event.source} action=${event.actionMasked} x=${event.x} y=${event.y}")
        return super.onGenericMotionEvent(event)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (event.actionMasked == MotionEvent.ACTION_UP) sendKey("tap", -1)
        return true
    }

    private fun sendKey(name: String, code: Int, scan: Int = -1, device: String = "") {
        log("input $name")
        ws?.send(JSONObject().put("type", "key").put("name", name).put("code", code)
            .put("scan", scan).put("device", device).toString())
    }

    private var worn: Boolean? = null
    private var imuOn = false
    private val imuBuf = org.json.JSONArray()
    private var imuLastSend = 0L

    private fun setImu(on: Boolean) {
        val sm = getSystemService(Context.SENSOR_SERVICE) as android.hardware.SensorManager
        if (on && !imuOn) {
            listOf(android.hardware.Sensor.TYPE_GYROSCOPE, android.hardware.Sensor.TYPE_ACCELEROMETER,
                   android.hardware.Sensor.TYPE_GAME_ROTATION_VECTOR, android.hardware.Sensor.TYPE_PROXIMITY,
                   android.hardware.Sensor.TYPE_LIGHT).forEach { type ->
                sm.getDefaultSensor(type)?.let { sm.registerListener(this, it, 20000) }  // 50 Hz
            }
        } else if (!on && imuOn) {
            sm.unregisterListener(this)
            sm.getDefaultSensor(android.hardware.Sensor.TYPE_LOW_LATENCY_OFFBODY_DETECT, true)?.let {
                sm.registerListener(this, it, android.hardware.SensorManager.SENSOR_DELAY_NORMAL) }
        }
        imuOn = on
        log("imu streaming=$on")
    }

    override fun onSensorChanged(e: android.hardware.SensorEvent) {
        if (imuOn && e.sensor.type != android.hardware.Sensor.TYPE_LOW_LATENCY_OFFBODY_DETECT) {
            val row = org.json.JSONArray().put(e.sensor.type).put(e.timestamp / 1_000_000)
            e.values.forEach { row.put(it.toDouble()) }
            imuBuf.put(row)
            val now = System.currentTimeMillis()
            if (now - imuLastSend > 100 && imuBuf.length() > 0) {
                imuLastSend = now
                ws?.send(JSONObject().put("type", "imu").put("rows", org.json.JSONArray(imuBuf.toString())).toString())
                while (imuBuf.length() > 0) imuBuf.remove(0)
            }
        }
        if (e.sensor.type == android.hardware.Sensor.TYPE_LOW_LATENCY_OFFBODY_DETECT) {
            val on = e.values[0] > 0.5f  // 1.0 = on body
            if (on != worn) {
                worn = on
                log("worn=$on")
                ws?.send(JSONObject().put("type", "worn").put("value", on).toString())
            }
        }
    }

    override fun onAccuracyChanged(sensor: android.hardware.Sensor?, accuracy: Int) {}

    // Home app: the wearer can never "exit" Lucia.
    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {}

    private fun log(s: String) = Log.i("Lucia", s)

    override fun onDestroy() {
        super.onDestroy()
        camera?.apply { setPreviewCallback(null); stopPreview(); release() }
        recorder?.release(); player?.release(); tts?.shutdown()
    }
}
