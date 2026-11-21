/* Simulator controller: fakes the glasses (keys, mic, camera, sensors) and drives the lens iframe.
   Mock mode: MockBrain answers from sim/mock-kb.js, speech via the browser's speechSynthesis.
   Live mode: talks to a real hub's /ws/lens (the lens iframe connects to the same hub). */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var lens = $("lens"), frame = $("lens-frame"), KB = window.MockBrain.kb;
  var mode = "mock", live = null, armedUntil = 0, followupUntil = 0, playbackGeneration = 0, worn = false;

  // ---------------------------------------------------------------- helpers
  function log(kind, text) {
    var li = document.createElement("li");
    li.innerHTML = "<b></b> <span></span>";
    li.querySelector("b").textContent = new Date().toLocaleTimeString() + " " + kind;
    li.querySelector("span").textContent = text || "";
    $("log").insertBefore(li, $("log").firstChild);
  }
  function show(msg) { if (mode === "mock") lens.contentWindow.postMessage(msg, "*"); }
  function speak(text, rate) {
    if (!window.speechSynthesis || mode !== "mock") return;
    var generation = ++playbackGeneration;
    speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(text);
    u.onend = function () { if (generation === playbackGeneration) followupUntil = Date.now() + 15000; };
    u.rate = 0.95 * (rate || 1); speechSynthesis.speak(u);
  }
  function respond(r) {
    show(r);
    if (r.intent === "speech_stop") { playbackGeneration++; if (window.speechSynthesis) speechSynthesis.cancel(); followupUntil = 0; }
    else { speak(r.speech, r.speech_rate); followupUntil = Date.now() + 15000; }
    log("lucia", r.speech + "  [" + r.intent + "]");
    if (r.alert) text(r.alert);
  }
  function text(msg) {
    var t = $("texts"); if (t.querySelector(".muted")) t.innerHTML = "";
    var p = document.createElement("p"); p.textContent = KB.app + ": " + msg; t.appendChild(p);
    log("imessage → caregiver", msg);
  }

  // ---------------------------------------------------------------- glasses inputs
  function arm(why) {
    armedUntil = Date.now() + 8000;
    if (mode === "live") return send({ type: "key", name: /^(tap|long_press|swipe_back|swipe_forward)$/.test(why) ? why : "tap" });
    show({ type: "state", value: "listening" }); log("listening", why);
  }
  function hear(utterance) {
    log("heard", utterance);
    var m = utterance.match(/^\s*(lucia|lucía|lucy a)[\s,.!?-]*(.*)$/i);
    var armed = Date.now() < armedUntil, q = m ? m[2] : utterance;
    var control = window.MockBrain.control(q);
    if (!m && !armed && !(control && Date.now() < followupUntil)) return log("ignored", "no wake word and not armed (tap first or start with “Lucia”)");
    if (mode === "live") return send({ type: "ask", text: q || utterance });
    if (!q || (!control && q.split(" ").length < 2)) return arm("wake word");
    armedUntil = 0;
    show({ type: "state", value: "thinking" });
    setTimeout(function () { respond(window.MockBrain.answer(q)); }, 350);
  }
  function walkIn(id) {
    if (mode === "live") return send({ type: "seen", person: id || null });
    window.MockBrain.see(id || null);
    log("camera", id ? KB.people[id].name + " is in view" : "unknown face in view");
    if (id) respond(window.MockBrain.introCard(id));
  }

  // ---------------------------------------------------------------- live mode
  function send(m) { if (live && live.readyState === 1) { live.send(JSON.stringify(m)); log("→ hub", JSON.stringify(m)); } else log("error", "not connected to hub"); }
  function setMode(m) {
    mode = m;
    if (live) { live.onclose = null; live.close(); live = null; }
    var pill = $("conn-pill");
    if (m === "mock") {
      lens.src = "../lens/index.html?ws=off";
      pill.textContent = "mock"; pill.className = "pill on";
      return;
    }
    var http = $("hub-url").value.replace(/\/$/, ""), ws = http.replace(/^http/, "ws") + "/ws/lens";
    lens.src = "../lens/index.html?ws=" + encodeURIComponent(ws);
    live = new WebSocket(ws);
    pill.textContent = "connecting…"; pill.className = "pill";
    live.onopen = function () { pill.textContent = "live: " + http; pill.className = "pill on"; log("hub", "connected " + ws); };
    live.onclose = function () { pill.textContent = "hub offline"; pill.className = "pill"; };
    live.onmessage = function (e) { log("hub →", e.data.slice(0, 160)); };
    var cg = new WebSocket(http.replace(/^http/, "ws") + "/ws/caregiver");
    cg.onmessage = function (e) { try { var ev = JSON.parse(e.data); if (ev.type === "alert") text(ev.text + " (" + ev.status + ")"); } catch (err) {} };
  }
  Array.prototype.forEach.call(document.querySelectorAll("input[name=mode]"), function (r) {
    r.addEventListener("change", function () { setMode(r.value); });
  });

  // ---------------------------------------------------------------- UI wiring
  $("b-tap").onclick = function () { arm("tap"); };
  // any touch on the temple asks: the wearer never has to remember which gesture
  $("b-hold").onclick = function () { arm("long_press"); };
  // head gestures (IMU): only mean something right after Lucia asks a yes/no question
  $("b-nod").onclick = function () { log("imu", "nod"); if (mode === "live") send({ type: "gesture", name: "nod" }); };
  $("b-shake").onclick = function () { log("imu", "shake"); if (mode === "live") send({ type: "gesture", name: "shake" }); };
  $("b-left").onclick = function () { arm("swipe_back"); };
  $("b-right").onclick = function () { arm("swipe_forward"); };
  $("b-back").onclick = function () { log("key", "back (swallowed: Lucia never closes)"); };
  $("b-worn").onclick = function () {
    worn = true; log("sensor", "glasses put on");
    if (mode === "live") send({ type: "worn", value: true }); else respond(window.MockBrain.greeting());
  };
  $("b-stranger").onclick = function () { walkIn(null); };
  $("person").onchange = function (e) { if (e.target.value) walkIn(e.target.value); e.target.value = ""; };
  $("say-form").onsubmit = function (e) { e.preventDefault(); var v = $("say").value.trim(); if (v) hear(v); $("say").value = ""; };
  Array.prototype.forEach.call(document.querySelectorAll("[data-state]"), function (b) {
    b.onclick = function () { var s = b.getAttribute("data-state"); show(s === "clear" ? { type: "clear" } : { type: "state", value: s }); };
  });
  var disc = false;
  $("b-disc").onclick = function () { disc = !disc; show({ type: "conn", value: !disc }); };
  $("b-distress").onclick = function () { hear("Lucia, I want to go home"); };
  $("b-unknown").onclick = function () { walkIn(null); hear("Lucia, who is this?"); };
  $("b-long").onclick = function () {
    show({ type: "card", title: "Long answer test", intent: "kb:faq", ttl_ms: 9000,
      lines: ["This line is about thirty-four c", "second line of the answer goes", "third line gets cut off with an…"] });
  };
  document.addEventListener("keydown", function (e) {
    if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); arm("tap"); }
    else if (e.key === "ArrowLeft") $("b-left").click();
    else if (e.key === "ArrowRight") $("b-right").click();
    else if (e.key === "Escape") $("b-back").click();
  });

  $("t-green").onchange = function (e) { frame.classList.toggle("green", e.target.checked); };
  $("t-see").onchange = function (e) { frame.classList.toggle("see-through", e.target.checked); };
  $("t-bar").onchange = function (e) { $("statusbar").classList.toggle("off", !e.target.checked); };
  $("t-zoom").onchange = function (e) { frame.classList.toggle("zoom", e.target.checked); };
  setInterval(function () { $("sb-clock").textContent = new Date().toTimeString().slice(0, 5); }, 1000);

  // people dropdown + scripted question chips (every question in the knowledge base)
  Object.keys(KB.people).forEach(function (id) {
    var o = document.createElement("option"); o.value = id; o.textContent = KB.people[id].name + " walks in"; $("person").appendChild(o);
  });
  var groups = { built: ["who is this?", "what day is it?", "what time is it?", "I want to go home", "what am I looking at?"] };
  KB.entries.forEach(function (e) {
    var g = e.scope === "person" ? KB.people[e.subject].first : e.scope;
    (groups[g] = groups[g] || []).push(e.questions[0]);
  });
  Object.keys(groups).forEach(function (g) {
    var h = document.createElement("div"); h.className = "group"; h.textContent = g; $("chips").appendChild(h);
    groups[g].forEach(function (q) {
      var b = document.createElement("button"); b.textContent = q;
      b.onclick = function () { hear("Lucia, " + q); };
      $("chips").appendChild(b);
    });
  });

  lens.addEventListener("load", function () {
    show({ type: "config", hint: KB.hint || 'Say "Lucia" or hold right side' });
  });
  setMode("mock");
  log("ready", Object.keys(KB.people).length + " people, " + KB.entries.length + " answers loaded from mock-kb.js");
})();
