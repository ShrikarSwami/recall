/* Lucia lens renderer. Plain ES2018 for Chrome 74 (Android 9 WebView):
   NO optional chaining (?.), NO nullish (??), NO top-level await, NO ES modules needed.

   Messages it renders (from the hub over WebSocket, or from the simulator via postMessage):
     {"type":"config", "hint":"Say \"Lucia\" or hold right side", "app":"Lucia", "patient":"Somya", "now": 1795229364000, "tz": -300}
     {"type":"state",  "value":"idle" | "listening" | "thinking"}
     {"type":"card",   "title":"Dev", "lines":["This is Dev. He's on","your team."], "ttl_ms":8000,
                       "intent":"who_is_this" | "proactive_intro" | "greeting" | "distress" | "unknown" | "freeform" | "time" | "kb:person" | ...,
                       "prompt":"Hear more about Dev?\nNod or say \"yes\"  ·  shake or say \"no\""}   (optional: Lucia asked a yes/no question)
     {"type":"clear"}
     {"type":"conn",   "value":true|false}       (simulator only; real lens derives it from the socket)

   URL params:
     ?ws=ws://host:9100/ws/lens   connect to that hub (default: same host as this page, if served by the hub)
     ?ws=off                      don't connect; only listen to postMessage (simulator mock mode)
*/
(function () {
  "use strict";

  var el = function (id) { return document.getElementById(id); };
  var card = el("card"), title = el("card-title"), body = el("card-body"), prompt = el("card-prompt");
  var status = el("status"), statusText = el("status-text");
  var hint = el("hint"), clock = el("clock"), offline = el("offline");
  var hideTimer = null;
  var clockOffset = 0;   // hub time - device time
  var tzMin = null;      // hub's UTC offset in minutes; the M6 ships set to China time (UTC+8)

  function setCard(msg) {
    title.textContent = msg.title || "";
    body.textContent = (msg.lines || []).join("\n");
    prompt.textContent = msg.prompt || "";
    prompt.className = msg.prompt ? "" : "hidden";
    card.className = "intent-" + String(msg.intent || "none").replace(/[^a-z_]/gi, "_");
    if (hideTimer) clearTimeout(hideTimer);
    hideTimer = setTimeout(function () { card.className += " hidden"; }, msg.ttl_ms || 8000);
    setState("idle");
  }

  function setState(v) {
    if (v === "listening") { status.className = ""; statusText.textContent = "Listening…"; }
    else if (v === "thinking") { status.className = ""; statusText.textContent = "One moment…"; }
    else { status.className = "hidden"; }
  }

  function render(msg) {
    if (!msg || !msg.type) return;
    if (msg.type === "config") {
      if (msg.hint) hint.textContent = msg.hint;
      if (msg.now) clockOffset = msg.now - Date.now();
      if (typeof msg.tz === "number") tzMin = msg.tz;
      tick();
    }
    else if (msg.type === "card") setCard(msg);
    else if (msg.type === "state") setState(msg.value);
    else if (msg.type === "clear") { card.className = "hidden"; setState("idle"); }
    else if (msg.type === "conn") offline.className = msg.value ? "hidden" : "";
  }
  window.LuciaLens = { render: render };

  function tick() {
    var now = Date.now() + clockOffset, d, h, m;
    if (tzMin === null) { d = new Date(now); h = d.getHours(); m = d.getMinutes(); }
    else { d = new Date(now + tzMin * 60000); h = d.getUTCHours(); m = d.getUTCMinutes(); }
    h = h % 12 || 12; m = ("0" + m).slice(-2);
    clock.textContent = h + ":" + m;
  }
  tick(); setInterval(tick, 10000);

  // Simulator (parent page) drives the lens with postMessage.
  window.addEventListener("message", function (e) {
    var msg = e.data;
    if (typeof msg === "string") { try { msg = JSON.parse(msg); } catch (err) { return; } }
    render(msg);
  });

  // Hub connection.
  var param = (location.search.match(/[?&]ws=([^&]+)/) || [])[1];
  var wsUrl = param ? decodeURIComponent(param)
            : (location.protocol.indexOf("http") === 0 ? "ws://" + location.host + "/ws/lens" : null);
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
