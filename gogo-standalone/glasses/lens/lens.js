/* Go-go lens renderer. Plain ES5 + a few ES2015 bits, all fine in Chrome 74 (Android 9 WebView).
   NO optional chaining (?.), NO nullish (??), NO replaceAll/.at()/structuredClone.

   Messages (from the hub over WebSocket later, or from the simulator via postMessage):
     {"type":"config",  "hint":"Say \"Gogo\" to ask", "now":<epoch ms>, "tz":-300}
     {"type":"card",    "title":"You're safe", "lines":["..."], "icon":"shield", "tag":"SAFE", "alert":false, "ring":false, "ttl_ms":0}
     {"type":"clear"}
     {"type":"avatar",  "pose":"idle|wave|point|walk|sleepy|calm|alert|cheer", "emo":"warm|happy|proud|curious|concerned|sleepy|calm|alert",
                        "pos":"left|center|right", "far":0..1, "face":"user|away", "dir":"left|right", "talking":true|false,
                        "action":"twirl|greet", "size":"big|normal"}
     {"type":"power",   "on":true|false}          (false = the lens shows nothing, until it is started)
     {"type":"splash",  "on":true, "ms":5000}     (the GOGO logo; the compass turns once in 5 s; hides itself after ms)
     {"type":"arrows",  "value":"left|right|both|"}
     {"type":"ring",    "phase":"in|out", "label":"Breathe in..."}
     {"type":"tapnote", "text":"Tap when you're ready"}     (empty text hides it)
     {"type":"battery", "on":true, "pct":15}
   Messages from the Go-go hub (all supported, so this lens is a drop-in for lens/ on the glasses):
     {"type":"state", "value":"idle|listening|thinking"}   {"type":"conn", "value":true|false}
     {"type":"card", "title", "lines", "intent":"greeting|who_is_this|kb:place|time|distress|...", "prompt":"Nod or say yes", "ttl_ms"}
       (a card with no icon gets a stamp chosen from its intent, see INTENT_STAMP)
   URL params: ?ws=ws://host:9100/ws/lens (default: the host that served this page), ?ws=off = postMessage only
*/
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var card = $("card"), title = $("title"), lines = $("lines"), slot = $("slot");
  var hideTimer = null, clockOffset = 0, tzMin = null;
  var splashTimer = null;

  // ------------------------------------------------------------ card, sticker, arrows, ring
  function setSticker(icon, tag, alert) {
    if (!icon) { slot.className = "empty"; slot.innerHTML = ""; return; }
    slot.className = "";
    var scene = document.getElementById("s-" + icon), t = String(tag || "").toUpperCase();
    var art = scene ? '<use xlink:href="#s-' + icon + '" x="13" y="12" width="70" height="70"/>'
                    : '<svg class="line" x="28" y="22" width="40" height="40" viewBox="0 0 64 64"><use xlink:href="#i-' + icon + '"/></svg>';
    slot.innerHTML = '<div class="sticker pop' + (alert ? " alert" : "") + '"><svg class="stamp" viewBox="0 0 96 112">' +
      '<rect width="96" height="112" fill="currentColor" mask="url(#perf)"/>' +
      '<rect class="panel" x="8" y="8" width="80" height="96" rx="2"/>' +
      '<rect x="11" y="11" width="74" height="90" rx="1" fill="none" stroke="currentColor" stroke-width="1.2"/>' +
      art + '<text class="stag" x="48" y="98" text-anchor="middle"' + (t.length > 8 ? ' textLength="62" lengthAdjust="spacingAndGlyphs"' : "") + "></text></svg></div>";
    slot.querySelector(".stag").textContent = t;
  }
  function clearCard() { $("prompt").textContent = ""; title.textContent = ""; lines.textContent = ""; slot.className = "empty"; slot.innerHTML = ""; }
  // hub answers carry an intent but no icon: give each a calm stamp
  var INTENT_STAMP = { greeting: ["shield", "WITH YOU"], proactive_intro: ["person-visitor", "HELLO"], who_is_this: ["person-visitor", "HELLO"], who_is: ["person-visitor", "HELLO"],
    "kb:person": ["person-visitor", "FRIEND"], "kb:place": ["home", "HERE"], "kb:patient": ["person", "YOU"], time: ["timer", "TODAY"], distress: ["shield", "SAFE"] };
  function setCard(m) {
    if (!m.icon && m.intent && INTENT_STAMP[m.intent]) { m.icon = INTENT_STAMP[m.intent][0]; m.tag = m.tag || INTENT_STAMP[m.intent][1]; }
    if (m.ttl_ms === undefined && m.intent) m.ttl_ms = 8000;
    $("prompt").textContent = m.prompt || "";
    title.textContent = m.title || "";
    lines.textContent = (m.lines || []).join("\n");
    if (m.ring) { slot.className = ""; slot.innerHTML = '<div id="ring"></div>'; } else setSticker(m.icon, m.tag, m.alert);
    card.className = (!m.ring && !m.icon && !(m.lines && m.lines.length)) ? "center" : "";
    if (hideTimer) clearTimeout(hideTimer);
    if (m.ttl_ms) hideTimer = setTimeout(clearCard, m.ttl_ms);
  }
  function setArrows(a) {
    $("arL").className = "arrow" + (a === "left" || a === "both" ? " on" : "");
    $("arR").className = "arrow" + (a === "right" || a === "both" ? " on" : "");
  }
  function setRing(phase, label) {
    var r = $("ring"); if (r) r.className = phase === "in" ? "in" : "";
    if (label) lines.textContent = label;
  }

  // ------------------------------------------------------------ the guide: sprites baked from a 3D squirrel model
  var AV = { pose: "idle", emo: null, talking: false, dir: "right" };
  var TG = { x: 0, far: 0, face: "user" }, CUR = { x: 0, far: 0 };
  var XS = { left: -0.72, center: 0, right: 0.72 };
  var POSE_EMO = { idle: "warm", wave: "happy", point: "warm", walk: "warm", sleepy: "sleepy", calm: "calm", alert: "alert", cheer: "proud" };
  var wrap = $("sqwrap"), sq = $("sq"), jumper = $("jumper"), sctx = sq.getContext("2d");
  var MAPD = window.SQ_MAP || { frames: {}, cell: 160 }, MAP = MAPD.frames, CELL = MAPD.cell;
  var sheet = new Image(), sheetReady = false;
  sheet.onload = function () { sheetReady = true; lastDraw = ""; };
  sheet.src = "squirrel_sheet.png";
  // a second, sharper set of frames for the moments when the squirrel is shown big
  var BIGD = window.SQ_BIG_MAP || { frames: {}, cell: 320 }, BMAP = BIGD.frames, BCELL = BIGD.cell, bigSheet = new Image(), bigReady = false;
  bigSheet.onload = function () { bigReady = true; lastDraw = ""; };
  bigSheet.src = "squirrel_big_sheet.png";
  var BK = 1, wantBig = false;
  var yaw = 0, lastYawStep = 0, runT = 0, lastDraw = "", lastXform = "", lastT = (window.performance && performance.now) ? performance.now() : 0;
  var moving = false, lastDip = "";
  // a short scripted move: the Go-go twirl = wave, hop, spin all the way round, bow, wave
  var ACT = null, TWIRL = [0, 45, 90, 135, 180, 225, 270, 315, 0];
  // the greeting: a bow, then a wave. 4 seconds in all.
  function greetFrame(now) {
    var e = now - ACT.t0;
    if (e < 300) return { name: "emo_happy", mir: false };
    if (e < 700) return { name: "bow_0", mir: false, dip: 0.5 };
    if (e < 1500) return { name: "bow_1", mir: false, dip: 1 };
    if (e < 1900) return { name: "bow_0", mir: false, dip: 0.5 };
    if (e < 4000) return { name: "wave_" + (Math.floor(e / 160) % 4), mir: false };
    return null;
  }
  function actFrame(now) {
    if (ACT.name === "greet") return greetFrame(now);
    var e = now - ACT.t0, k;
    if (e < 900) return { name: "wave_" + (Math.floor(e / 160) % 4), mir: false };
    if (e < 2100) {
      if (!ACT.hopped) { ACT.hopped = true; setClass(jumper, "hop", true); setTimeout(function () { setClass(jumper, "hop", false); }, 1300); }
      k = TWIRL[Math.min(TWIRL.length - 1, Math.floor((e - 900) / 135))];
      return { name: "idle_" + (k <= 180 ? k : 360 - k), mir: k > 180 };
    }
    if (e < 2400) return { name: "bow_0", mir: false };
    if (e < 2900) return { name: "bow_1", mir: false };
    if (e < 3200) return { name: "bow_0", mir: false };
    if (e < 3900) return { name: "wave_" + (Math.floor(e / 160) % 4), mir: false };
    return null;
  }

  function drawFrame(name, mirror) {
    var useBig = BK > 1.3 && bigReady && BMAP[name], f = useBig ? BMAP[name] : MAP[name];
    if (!f || !sheetReady) return;
    var key = name + (mirror ? "m" : "") + (useBig ? "B" : ""); if (key === lastDraw) return; lastDraw = key;
    sctx.setTransform(1, 0, 0, 1, 0, 0); sctx.clearRect(0, 0, sq.width, sq.height);
    if (mirror) { sctx.translate(sq.width, 0); sctx.scale(-1, 1); }
    if (useBig) sctx.drawImage(bigSheet, f[0] * BCELL, f[1] * BCELL, BCELL, BCELL, 0, 0, sq.width, sq.height);
    else sctx.drawImage(sheet, f[0] * CELL, f[1] * CELL, CELL, CELL, 0, 0, sq.width, sq.height);
  }
  function setClass(el, cls, on) { var has = el.className.indexOf(cls) >= 0; if (on && !has) el.className += " " + cls; else if (!on && has) el.className = el.className.replace(" " + cls, "").replace(cls, ""); }
  function guideFrame() {
    var now = performance.now(), dt = Math.min(0.1, (now - lastT) / 1000); lastT = now;
    var dx = TG.x - CUR.x, df = TG.far - CUR.far, tx = Math.abs(dx) / 0.9, tf = Math.abs(df) / 0.28;
    moving = tx > 0.02 || tf > 0.02;
    if (tx > 0.02) CUR.x += (dx > 0 ? 1 : -1) * Math.min(Math.abs(dx), 0.9 * dt);
    if (tf > 0.02) CUR.far += (df > 0 ? 1 : -1) * Math.min(Math.abs(df), 0.28 * dt);

    // facing: 0 = toward you, 180 = back to you, 90 = facing screen-right (the other three are mirrored)
    var want = TG.face === "away" ? 180 : 0;
    if (moving) want = tf >= tx ? (df > 0 ? 180 : 0) : (dx > 0 ? 90 : 270);
    if (now - lastYawStep > 80 && yaw !== want) {
      var diff = ((want - yaw + 540) % 360) - 180;
      yaw = (yaw + (diff > 0 ? 45 : -45) + 360) % 360; lastYawStep = now;
    }
    if (moving) runT += dt;
    var yb = yaw <= 180 ? yaw : 360 - yaw, mir = yaw > 180, name, emo = AV.emo || POSE_EMO[AV.pose] || "warm", t = now / 1000;
    if (moving) name = "run_" + yb + "_" + (Math.floor(runT * 11) % 6);
    else if (yaw !== 0) name = "idle_" + yb;
    else if (AV.pose === "wave") name = "wave_" + (Math.floor(t * 6) % 4);
    else if (AV.pose === "cheer") name = "cheer_" + (Math.floor(t * 6) % 4);
    else if (AV.pose === "point") { name = "pointR"; mir = AV.dir === "left"; }
    else if (AV.pose === "alert") name = "emo_alert";
    else {
      name = "emo_" + emo;
      if (AV.talking && (emo === "warm" || emo === "happy") && Math.floor(t * 6) % 2) name += "_talk";
    }
    var dip = 0;
    if (ACT) { var af = actFrame(now); if (af) { name = af.name; mir = af.mir; dip = af.dip || 0; } else ACT = null; }
    var dxf = dip ? "translateY(" + Math.round(14 * dip) + "px) scale(" + (1 + 0.04 * dip).toFixed(3) + "," + (1 - 0.10 * dip).toFixed(3) + ")" : "";
    if (dxf !== lastDip) { lastDip = dxf; jumper.style.webkitTransform = dxf; jumper.style.transform = dxf; }   // the bow: dip down and squash a little
    drawFrame(name, mir);
    setClass(sq, "breathe", !moving && !ACT);
    setClass(jumper, "jump", AV.pose === "cheer" && !moving && !ACT);
    setClass($("zzz"), "on", emo === "sleepy" && !moving);

    BK += ((wantBig ? 2.3 : 1) - BK) * Math.min(1, dt * 4);
    var s = (1 - 0.55 * CUR.far) * BK;
    var xf = "translate(" + Math.round(CUR.x * 220) + "px," + Math.round(-CUR.far * 100) + "px) scale(" + s.toFixed(3) + ")";
    if (xf !== lastXform) { lastXform = xf; wrap.style.webkitTransform = xf; wrap.style.transform = xf; }
  }
  setInterval(guideFrame, 33);

  // ------------------------------------------------------------ clock, hint, battery
  function tick() {
    var now = Date.now() + clockOffset, d, h, m;
    if (tzMin === null) { d = new Date(now); h = d.getHours(); m = d.getMinutes(); }
    else { d = new Date(now + tzMin * 60000); h = d.getUTCHours(); m = d.getUTCMinutes(); }   // the M6 ships set to China time
    h = h % 12 || 12; m = ("0" + m).slice(-2);
    $("clock").textContent = h + ":" + m;
  }
  tick(); setInterval(tick, 10000);

  // ------------------------------------------------------------ messages
  function render(msg) {
    if (!msg || !msg.type) return;
    var t = msg.type;
    if (t === "card") setCard(msg);
    else if (t === "clear") { if (hideTimer) clearTimeout(hideTimer); clearCard(); setArrows(""); $("tapnote").className = ""; }
    else if (t === "avatar") {
      if (msg.pose !== undefined) AV.pose = msg.pose || "idle";
      if (msg.emo !== undefined) AV.emo = msg.emo;
      if (msg.talking !== undefined) AV.talking = !!msg.talking;
      if (msg.dir !== undefined) AV.dir = msg.dir === "left" ? "left" : "right";
      if (msg.pos !== undefined && XS[msg.pos] !== undefined) TG.x = XS[msg.pos];
      if (msg.far !== undefined) TG.far = msg.far;
      if (msg.face !== undefined) TG.face = msg.face === "away" ? "away" : "user";
      if (msg.size !== undefined) wantBig = msg.size === "big";
      if (msg.action === "twirl" || msg.action === "greet") ACT = { name: msg.action, t0: performance.now(), hopped: false };
    }
    else if (t === "splash") {
      var sp = $("splash"); sp.className = msg.on ? "on" : "";
      if (splashTimer) clearTimeout(splashTimer);
      if (msg.on && msg.ms) splashTimer = setTimeout(function () { sp.className = ""; }, msg.ms);
    }
    else if (t === "power") $("sleep").className = msg.on ? "" : "on";
    else if (t === "state") {
      var st = $("status"), v = msg.value;
      st.textContent = v === "listening" ? "Listening…" : v === "thinking" ? "One moment…" : "";
      st.className = v === "listening" || v === "thinking" ? "on" : "";
      AV.emo = v === "listening" ? "curious" : v === "thinking" ? "calm" : null;
    }
    else if (t === "conn") $("offline").className = msg.value ? "" : "on";
    else if (t === "arrows") setArrows(msg.value || "");
    else if (t === "ring") setRing(msg.phase, msg.label);
    else if (t === "tapnote") { var n = $("tapnote"); n.textContent = msg.text || ""; n.className = msg.text ? "on" : ""; }
    else if (t === "battery") { $("batpct").textContent = (msg.pct != null ? msg.pct : 15) + "%"; $("bat").className = msg.on ? "on" : ""; }
    else if (t === "config") {
      if (msg.hint) $("hint").textContent = msg.hint;
      if (msg.now) clockOffset = msg.now - Date.now();
      if (typeof msg.tz === "number") tzMin = msg.tz;
      tick();
    }
  }
  window.LuciaLens = { render: render };

  window.addEventListener("message", function (e) {
    var msg = e.data;
    if (typeof msg === "string") { try { msg = JSON.parse(msg); } catch (err) { return; } }
    render(msg);
  });

  // hub connection (same as the plain lens): the hub serves this page at /lens/ and the socket at /ws/lens
  var param = (location.search.match(/[?&]ws=([^&]+)/) || [])[1];
  var wsUrl = param ? decodeURIComponent(param) : (location.protocol.indexOf("http") === 0 ? "ws://" + location.host + "/ws/lens" : null);
  if (!wsUrl || wsUrl === "off") return;
  var downSince = null;
  function connect() {
    var ws = new WebSocket(wsUrl);
    ws.onopen = function () { downSince = null; render({ type: "conn", value: true }); };
    ws.onmessage = function (e) { try { render(JSON.parse(e.data)); } catch (err) {} };
    ws.onclose = function () {
      if (!downSince) downSince = Date.now();
      setTimeout(function () { if (downSince && Date.now() - downSince > 3000) render({ type: "conn", value: false }); }, 3100);
      setTimeout(connect, 1500);
    };
  }
  connect();
})();
