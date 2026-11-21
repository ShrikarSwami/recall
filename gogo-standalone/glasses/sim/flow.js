/* Simulator shell: plays the scripted moments and drives the lens with messages, exactly like the hub will.
   It also talks to the care server (profile, weather, dashboard instructions, event log) so the dashboard has real data.
   The lens (../lens/) never knows it is being simulated. Runs in Chromium 74 as well as modern browsers. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var lens = $("lens");
  var CFG = {
    name: "Mike", partner: "Anna", voice: true, age: "74", charm: "handsome", place: "CUNY, Brooklyn", weather: "sunny", auto: false,
    bag: "Right behind you", gate: "top right", goals: [], routeTo: [], routeBack: [],
    sky: "sunny", chill: "a little chilly", temp: "", live: false
  };

  // ------------------------------------------------------------ the short scripts (kept for the individual moments)
  var SCRIPTS = {
    onboard: [
      { splash: 5000 },
      { t: "Hi, I'm Gogo", l: [], big: true, pose: "idle", pos: "center", action: "greet", say: "Hi, I'm Gogo.", dur: 4000 },
      { t: "I'm with you", l: ["I'll get you through", "the day"], icon: "shield", tag: "WITH YOU", pose: "wave", say: "I'll get you through the day.", hold: 1500 },
      { t: "You're {name}", l: ["{age} years young,", "and very {charm}"], icon: "person", tag: "YOU", pose: "cheer", say: "You're {name}. {age} years young, and still very {charm}.", hold: 1800 },
      { t: "You're here", l: ["{place}", "{skyTitle} out"], icon: "{skyIcon}", tag: "{skyTag}", pose: "idle", say: "Right now, you're at {place}. {weatherSay}", hold: 2200 },
      { t: "Look around", l: ["Take your time"], icon: "eye", tag: "LOOK", arrows: "both", pose: "idle", emo: "curious", say: "Take a moment. Look around you. There's nothing to do yet.", hold: 3000 },
      { t: "Ready?", l: ["Tap when you are"], icon: "smile", tag: "READY", pose: "idle", say: "Whenever you're ready, give a little tap, and I'll show you who's around.", tap: true, tapHint: "Tap when you're ready" }
    ],
    morning: [
      { t: "Good morning", l: ["You're safe"], icon: "shield", tag: "SAFE", pose: "wave", pos: "center", say: "Good morning, {name}. You're safe.", hold: 1200 },
      { t: "You're {name}", l: ["{partner} is next to you"], icon: "person", tag: "YOU", pose: "idle", say: "Your name is {name}. {partner}, your wife, is right next to you.", hold: 1500 },
      { t: "At home", l: ["In your own bed"], icon: "home", tag: "HOME", say: "You're at home, in your own bed. Nothing is wrong.", hold: 1500 },
      { t: "Breathe with me", l: ["One slow breath"], ring: 2, pose: "calm", say: "Let's take two slow breaths together. In, and out." },
      { t: "Look around", l: ["Take your time"], icon: "eye", tag: "LOOK", arrows: "both", pose: "idle", emo: "curious", say: "Now look around the room. There's nothing to do yet. Take your time.", hold: 3500 },
      { t: "First: water", l: ["On the table by your bed"], icon: "drop", tag: "FIRST", pose: "point", face: "right", say: "First, a glass of water. It's on the table by your bed.", tap: true },
      { t: "Lovely, {name}", l: ["Next: breakfast"], icon: "cup", tag: "NEXT", pose: "cheer", say: "Lovely, {name}. Next is breakfast. {partner} is in the kitchen.", hold: 2000 }
    ],
    short: [
      { t: "Welcome back", l: ["You're still at home", "It's {time}"], icon: "home", tag: "HOME", pose: "wave", pos: "center", say: "Welcome back, {name}. You're still at home. It's {time}.", hold: 2500 }
    ],
    long: [
      { t: "Hello, {name}", l: ["You had a rest"], icon: "moon", tag: "REST", pose: "wave", pos: "center", say: "Hello, {name}. You had a nice rest. It's {time}.", hold: 1500 },
      { t: "At home", l: ["In the living room"], icon: "home", tag: "HOME", pose: "idle", say: "You're at home, in the living room. You're safe.", hold: 1500 },
      { t: "Next: tea", l: ["{partner} is making it"], icon: "cup", tag: "NEXT", pose: "point", face: "right", say: "Next, a cup of tea. {partner} is in the kitchen making it.", tap: true }
    ],
    newperson: [
      { t: "Someone's here", l: ["On your right"], icon: "person-visitor", tag: "HELLO", arrows: "right", pose: "point", pos: "left", face: "right", emo: "curious", say: "Someone is here, on your right. They look friendly.", hold: 1500 },
      { t: "Say hello", l: ["Ask: \"What's your name?\""], icon: "smile", tag: "SAY", arrows: "right", pose: "idle", pos: "left", say: "Say hello. You can ask: what's your name?", tap: true, tapHint: "Tap when they answer" },
      { t: "Sam", l: ["You just met"], icon: "person-visitor", tag: "NEW FRIEND", pose: "cheer", pos: "center", say: "Lovely. This is Sam. You met just now. I'll remember it for you.", hold: 2500 }
    ],
    known: [
      { t: "Priya", l: ["Your daughter"], icon: "person-female", tag: "FAMILY", arrows: "left", pose: "point", pos: "right", face: "left", emo: "happy", say: "Look to your left. That's Priya, your daughter. She's so glad to see you.", hold: 1500 },
      { t: "Say hello", l: ["\"Hi, Priya\""], icon: "smile", tag: "SAY", arrows: "left", pose: "idle", pos: "right", say: "Say hello to Priya. Just: hi, Priya.", tap: true }
    ],
    battery: [
      { t: "I'm getting sleepy", l: ["My battery is low"], icon: "battery", tag: "15%", battery: true, pose: "sleepy", pos: "center", say: "{name}, I'm getting a little sleepy. My battery is low. Let's help me charge. It's easy.", hold: 1500 },
      { t: "Take me off", l: ["Gently, with both hands"], icon: "glasses", tag: "STEP 1", pose: "idle", say: "Step one. Take the glasses off, gently, with both hands.", tap: true },
      { t: "Find the charger", l: ["On the table by your bed"], icon: "plug", tag: "STEP 2", pose: "point", pos: "left", face: "right", say: "Step two. The charger is on the table by your bed. The small white cable.", tap: true },
      { t: "Plug it in", l: ["Small end into the glasses"], icon: "plug", tag: "STEP 3", pose: "idle", pos: "center", say: "Step three. Plug the small end into the glasses. A little light will come on.", tap: true },
      { t: "Thank you", l: ["Rest now. I'll be here"], icon: "shield", tag: "THANKS", pose: "sleepy", say: "Thank you, {name}. I'll rest now. I'll be right here when you're back.", hold: 2000 }
    ],
    danger: [
      { t: "Careful", l: ["The stove is on"], icon: "warn", tag: "CAREFUL", alert: true, pose: "alert", pos: "center", say: "Careful, {name}. The stove is on. Let's step back together.", hold: 800 },
      { t: "Step back", l: ["Slowly, away from it"], icon: "back", tag: "SLOWLY", alert: true, pose: "idle", emo: "concerned", say: "Take one slow step back. That's it. {partner} is coming to help.", hold: 1800 },
      { t: "All good", l: ["You're safe"], icon: "shield", tag: "SAFE", pose: "wave", say: "Well done. You're safe. {partner} is here.", hold: 2000 }
    ],
    scared: [
      { t: "You're safe", l: ["I'm right here"], icon: "shield", tag: "SAFE", pose: "idle", pos: "center", emo: "concerned", say: "You're safe, {name}. I'm right here with you. {partner} knows, and she's coming.", hold: 1500 },
      { t: "Breathe with me", l: ["Nice and slow"], ring: 1, pose: "calm", say: "Let's breathe together. In, and out." },
      { t: "You're okay", l: ["{partner} is on her way"], icon: "home", tag: "HOME", pose: "wave", say: "You're okay. {partner} is on her way. I'll stay with you.", hold: 2500 }
    ],
    walk: [
      { t: "Let's walk", l: ["Follow me"], icon: "smile", tag: "COME ON", pose: "walk", far: 1, face: "away", pos: "center", say: "Let's walk to the kitchen together. Follow me. Take your time.", hold: 800 },
      { t: "Here we are", l: ["This is the kitchen"], icon: "home-kitchen", tag: "KITCHEN", pose: "wave", far: 1, face: "user", say: "Here we are. This is the kitchen.", hold: 2500 }
    ]
  };

  // ------------------------------------------------------------ helpers
  function send(m) { try { lens.contentWindow.postMessage(m, "*"); } catch (e) {} }
  var sleeping = true;   // the lens shows nothing until the camera is turned on
  function wake() { if (sleeping) { sleeping = false; send({ type: "power", on: true }); } }
  function goToSleep() { sleeping = true; send({ type: "power", on: false }); }
  function timeStr() { try { return new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }); } catch (e) { return ""; } }
  function cap(s) { s = String(s || ""); return s.charAt(0).toUpperCase() + s.slice(1); }
  function lowerFirst(s) { s = String(s || ""); return s.charAt(0).toLowerCase() + s.slice(1); }
  function fill(s) { return String(s).replace(/\{(\w+)\}/g, function (m, k) { return k === "time" ? timeStr() : (CFG[k] != null ? CFG[k] : m); }); }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function defer() { var d = {}; d.p = new Promise(function (r) { d.res = r; }); return d; }
  function wrapLines(text, n) {   // a sentence -> up to 3 short lens lines
    var words = String(text).split(/\s+/), out = [], cur = "";
    words.forEach(function (w) { if ((cur + " " + w).replace(/^\s/, "").length > n && cur) { out.push(cur); cur = w; } else cur = (cur + " " + w).replace(/^\s/, ""); });
    if (cur) out.push(cur);
    if (out.length > 3) { out = out.slice(0, 3); out[2] = out[2].replace(/\s*\S*$/, "") + "…"; }
    return out;
  }

  // ------------------------------------------------------------ care server: profile, weather, events, instructions
  function api(path) { return fetch(path, { cache: "no-store" }).then(function (r) { return r.json(); }); }
  function post(path, obj) {
    try { fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(obj) }).catch(function () {}); } catch (e) {}
  }
  function logEv(type, obj) { var o = obj || {}; o.type = type; post("/api/event", o); }

  function refreshDerived() {
    var h = new Date().getHours();
    CFG.daypart = h < 12 ? "morning" : (h < 17 ? "afternoon" : "evening");
    var sky = CFG.sky, chill = CFG.chill;
    var icons = { sunny: "sun", clear: "moon", "partly cloudy": "cloud", cloudy: "cloud", foggy: "cloud", drizzly: "rain", rainy: "rain", stormy: "rain", icy: "rain", snowy: "cloud" };
    CFG.skyIcon = icons[sky] || "cloud";
    CFG.skyTitle = sky === "clear" ? "Clear night" : cap(sky);
    CFG.weatherSay = (sky === "clear" ? "It's a clear night out" : "It's " + sky + " out") + (chill ? ", but " + chill : "") + ".";
    CFG.chillLine = chill ? cap(chill) : "Nice out there";
    CFG.skyTag = CFG.temp !== "" ? CFG.temp + "°F" : String(sky).toUpperCase();
    CFG.bagSay = lowerFirst(CFG.bag);
    CFG.WEATHER = String(sky).toUpperCase();
    CFG.goal1 = CFG.goals.length ? CFG.goals[0] : "get ready for the day";
  }
  function setWeatherNote(t) { var n = $("wstatus"); if (n) n.textContent = t; }
  function loadWeather() {
    return api("/api/weather").then(function (w) {
      if (w && w.ok) {
        CFG.live = true; CFG.sky = w.sky; CFG.chill = w.chill; CFG.temp = w.tempF;
        setWeatherNote("Live weather: " + w.sky + ", " + w.tempF + "°F (feels " + w.feelsF + "°F), from " + w.source + ".");
      } else {
        CFG.live = false; CFG.temp = "";
        CFG.sky = $("c-weather").value; CFG.chill = CFG.sky === "sunny" ? "" : "";
        setWeatherNote("No internet for the weather. Using the setting above.");
      }
      refreshDerived();
    }).catch(function () { CFG.live = false; setWeatherNote("Care server not reachable: using the settings above."); refreshDerived(); });
  }
  function loadCare() {
    return api("/api/state").then(function (st) {
      var p = st.profile || {}, pl = st.places || {};
      CFG.name = p.name || CFG.name; CFG.age = String(p.age || CFG.age); CFG.charm = p.gender === "woman" ? "beautiful" : "handsome";
      CFG.place = pl.city || CFG.place; CFG.bag = pl.bag || CFG.bag; CFG.gate = pl.gate || CFG.gate;
      CFG.routeTo = pl.routeToBathroom || []; CFG.routeBack = pl.routeBack || [];
      var d1 = (st.goals || [])[0]; CFG.goals = d1 ? d1.items : [];
      $("c-name").value = CFG.name; $("c-age").value = CFG.age; $("c-charm").value = CFG.charm; $("c-place").value = CFG.place;
      refreshDerived();
    }).catch(function () {});
  }

  // ------------------------------------------------------------ the demo day, built from the care plan
  function iconAt(arr, i) { return arr[Math.min(i, arr.length - 1)]; }
  function buildDemo() {
    refreshDerived();
    var S = [{ splash: 5000 }], gatePos = /left/i.test(CFG.gate) ? "left" : "right", other = gatePos === "left" ? "right" : "left";
    S.push({ t: "Hi, I'm Gogo", l: [], big: true, pose: "idle", pos: "center", action: "greet", say: "Hi, I'm Gogo.", dur: 4000, loc: "seat", ev: [{ type: "gaze", label: "a friendly squirrel", sim: true }] });
    S.push({ t: "I'm with you", l: ["I'll get you through", "the day"], icon: "shield", tag: "WITH YOU", pose: "wave", say: "I'll get you through the day.", hold: 1200 });
    S.push({ t: "You're {name}", l: ["{age} years young,", "and very {charm}"], icon: "person", tag: "YOU", pose: "cheer", say: "You're {name}. {age} years young, and still very {charm}.", hold: 1400 });
    S.push({ t: "You're here", l: ["at {place}", "with your friends"], icon: "friends", tag: "FRIENDS", pose: "idle", say: "You're at {place}, in the middle of a bunch of your friends.", hold: 1600,
      ev: [{ type: "attention", mode: "looking_around", secs: 6, sim: true }, { type: "gaze", label: "your friends", sim: true }] });
    S.push({ t: "{skyTitle}", l: ["{chillLine}"], icon: "{skyIcon}", tag: "{skyTag}", pose: "idle", say: "{weatherSay}", hold: 1500 });
    S.push({ t: "Your bag", l: ["{bag}"], icon: "bag", tag: "SAFE", pose: "point", face: "left", say: "Your bag is {bagSay}.", hold: 1500, ev: [{ type: "gaze", label: "his bag", sim: true }] });
    S.push({ t: "You're safe", l: ["Your friends know"], icon: "shield", tag: "SAFE", pose: "idle", emo: "warm", say: "Your friends know you're safe.", hold: 1300 });
    S.push({ t: "Today", l: wrapLines(CFG.goal1, 24), icon: "timer", tag: "TODAY", pose: "idle", say: "Today, we'll " + lowerFirst(CFG.goal1) + ".", hold: 1500 });
    S.push({ t: "Let's freshen up", l: ["I'll show you the way"], icon: "drop", tag: "FRESH UP", pose: "cheer", say: "Let's get you freshened up.", hold: 1000 });
    S.push({ t: "Where to?", l: ["Ask me where the", "bathroom is"], icon: "bath", tag: "ASK ME", pose: "idle", emo: "curious", say: "If you'd like to know where the bathroom is, just ask me.", waitAsk: true, tapHint: "Ask: where is the bathroom?" });
    S.push({ t: "The bathroom", l: ["Through the gate,", CFG.gate + " corner"], icon: "bath", tag: "THIS WAY", arrows: gatePos, pose: "point", face: gatePos, say: "The bathroom is through the gate, in the " + CFG.gate + " corner. I'll show you.", hold: 1600 });
    var to = CFG.routeTo, ticons = ["chair-stand", "gate", "forward", "bath"], i;
    for (i = 0; i < to.length; i++) {
      var st = { t: "Step " + (i + 1) + " of " + to.length, l: wrapLines(to[i], 26), icon: iconAt(ticons, i), tag: "STEP " + (i + 1), say: to[i], tap: true, tapHint: "Tap when you've done it" };
      if (i === 0) { st.pose = "idle"; st.pos = "center"; st.loc = "seat"; }
      else if (i === 1) { st.pose = "walk"; st.far = 0.75; st.face = "away"; st.pos = gatePos; st.arrows = gatePos; st.loc = "walking"; st.ev = [{ type: "attention", mode: "walking_straight", secs: 18, sim: true }, { type: "gaze", label: "the walkway", sim: true }]; }
      else if (i < to.length - 1) { st.pose = "wave"; st.far = 0.75; st.pos = gatePos; st.face = "user"; st.arrows = other; st.loc = "gate"; st.ev = [{ type: "attention", mode: "looking_around", secs: 9, sim: true }, { type: "gaze", label: "the gate", sim: true }]; }
      else { st.pose = "point"; st.far = 0.75; st.pos = gatePos; st.face = other; st.arrows = other; st.loc = "walking"; st.ev = [{ type: "gaze", label: "the bathroom door", sim: true }]; }
      S.push(st);
    }
    S.push({ t: "You made it", l: ["Well done, {name}"], icon: "shield", tag: "MADE IT", pose: "cheer", say: "You made it. Well done, {name}.", hold: 1100, loc: "bathroom" });
    S.push({ t: "Turn the tap on", l: ["Wet your hands"], icon: "drop-wash", tag: "WASH 1", pose: "idle", say: "Turn the tap on, and wet your hands.", tap: true, tapHint: "Tap when you've done it", ev: [{ type: "gaze", label: "the sink", sim: true }] });
    S.push({ t: "Rub, rub, rub", l: ["20 seconds"], ring: 1, countdown: 20, pose: "calm", say: "Now add a little soap. Rub your hands together for twenty seconds. I'll count with you." });
    S.push({ t: "Rinse", l: ["Under the water"], icon: "drop-wash", tag: "WASH 3", pose: "idle", say: "Now rinse your hands under the water.", tap: true, tapHint: "Tap when you've done it" });
    S.push({ t: "Dry your hands", l: ["Turn the tap off first"], icon: "hands", tag: "WASH 4", pose: "idle", say: "Turn the tap off, and dry your hands.", tap: true, tapHint: "Tap when you've done it" });
    S.push({ t: "All clean", l: ["Well done, {name}"], icon: "shield", tag: "CLEAN", pose: "cheer", say: "All clean. Well done, {name}.", hold: 1300 });
    var back = CFG.routeBack, bicons = ["gate", "forward", "chair"];
    for (i = 0; i < back.length; i++) {
      var sb = { t: "Back to your seat", l: wrapLines(back[i], 26), icon: iconAt(bicons, i), tag: "STEP " + (i + 1), say: back[i], tap: true, tapHint: "Tap when you've done it" };
      if (i === 0) { sb.pose = "walk"; sb.far = 0.6; sb.face = "away"; sb.pos = gatePos; sb.loc = "walking"; sb.ev = [{ type: "attention", mode: "walking_straight", secs: 14, sim: true }]; }
      else if (i < back.length - 1) { sb.pose = "wave"; sb.far = 0.4; sb.face = "user"; sb.pos = "center"; sb.loc = "walking"; sb.ev = [{ type: "attention", mode: "looking_around", secs: 8, sim: true }, { type: "gaze", label: "his friends", sim: true }]; }
      else { sb.pose = "point"; sb.face = "left"; sb.pos = "center"; sb.loc = "walking"; }
      S.push(sb);
    }
    S.push({ t: "Your seat", l: ["Next to your bag"], icon: "chair", tag: "SIT", pose: "idle", say: "This is your seat, next to your bag. Sit down slowly.", tap: true, tapHint: "Tap when you're sitting", loc: "seat", ev: [{ type: "attention", mode: "still", secs: 20, sim: true }] });
    S.push({ t: "Well done, {name}", l: ["You did it"], icon: "shield", tag: "DONE", pose: "cheer", action: "twirl", say: "Well done, {name}. You did it. I'm right here with you.", hold: 2600 });
    return S;
  }

  // ------------------------------------------------------------ steps -> lens messages
  function applyStep(s) {
    send({ type: "card", title: fill(s.t), lines: (s.l || []).map(fill), icon: s.ring ? null : (s.icon ? fill(s.icon) : null), tag: s.tag ? fill(s.tag) : s.tag, alert: !!s.alert, ring: !!s.ring });
    send({ type: "arrows", value: s.arrows || "" });
    send({ type: "battery", on: !!s.battery, pct: 15 });
    var av = { type: "avatar", size: s.big ? "big" : "normal", pose: s.pose || "idle", emo: s.emo || null, dir: s.face === "left" ? "left" : "right", far: s.far || 0, face: s.face === "away" ? "away" : "user" };
    if (s.pos) av.pos = s.pos;
    send(av);
    if (s.action) send({ type: "avatar", action: s.action });
  }
  function toIdle() {
    send({ type: "clear" }); send({ type: "battery", on: false });
    send({ type: "avatar", pose: "idle", emo: null, talking: false, pos: "center", far: 0, face: "user" });
  }

  function speakP(text) {
    return new Promise(function (res) {
      var done = false, fin = function () { if (!done) { done = true; res(); } };
      var est = Math.max(1200, text.split(/\s+/).length * 380) + 400;
      if (CFG.voice && window.speechSynthesis) {
        try {
          speechSynthesis.cancel();
          var u = new SpeechSynthesisUtterance(text);
          u.rate = 0.9; u.lang = "en-US"; u.onend = fin; u.onerror = fin;
          speechSynthesis.speak(u);
          setTimeout(fin, est + 7000);
          return;
        } catch (e) {}
      }
      setTimeout(fin, est);
    });
  }

  // ------------------------------------------------------------ the flow engine
  var run = 0, skipD = defer(), askD = defer(), moodT = null;
  function race(p) { return Promise.race([p, skipD.p]); }
  function skip() { skipD.res(); if (window.speechSynthesis) { try { speechSynthesis.cancel(); } catch (e) {} } }
  function stopAll() { run++; skip(); clearTimeout(moodT); toIdle(); }

  function ringRun(cycles, my) {
    var i = 0;
    function step() {
      if (i >= cycles || my !== run) return Promise.resolve();
      send({ type: "ring", phase: "in", label: "Breathe in…" });
      return race(sleep(4000)).then(function () {
        if (my !== run) return;
        send({ type: "ring", phase: "out", label: "…and out" });
        return race(sleep(4000));
      }).then(function () { i++; return step(); });
    }
    return step();
  }
  async function countdown(n, my) {
    for (var s = n; s > 0 && my === run; s--) {
      send({ type: "ring", phase: s % 2 ? "in" : "out", label: s + " seconds" });
      await race(sleep(1000));
    }
  }
  async function playSteps(steps, scene) {
    stopAll();
    var my = run;
    for (var i = 0; i < steps.length; i++) {
      if (my !== run) return;
      var s = steps[i];
      skipD = defer(); askD = defer(); var stepT0 = Date.now();
      if (s.splash) { send({ type: "splash", on: true, ms: s.splash }); await race(sleep(s.splash + 250)); continue; }
      applyStep(s);
      var said = fill(s.say);
      logEv("step", { text: fill(s.t), scene: scene });
      logEv("lucia", { text: said });
      if (s.loc) logEv("location", { place: s.loc, sim: true });
      (s.ev || []).forEach(function (e) { var o = {}; for (var k in e) o[k] = e[k]; var t = o.type; delete o.type; logEv(t, o); });
      send({ type: "avatar", talking: true });
      await race(speakP(said));
      send({ type: "avatar", talking: false });
      if (my !== run) return;
      if (s.ring && !s.countdown) { skipD = defer(); await ringRun(s.ring, my); if (my !== run) return; }   // (the soap step counts seconds instead of breathing)
      if (s.countdown) { skipD = defer(); await countdown(s.countdown, my); if (my !== run) return; }
      if (s.dur) { skipD = defer(); await race(sleep(Math.max(0, s.dur - (Date.now() - stepT0)))); }   // the whole step takes exactly this long
      if (s.hold) { skipD = defer(); await race(sleep(s.hold)); }
      if (s.tap || s.waitAsk) {
        skipD = defer();
        send({ type: "tapnote", text: s.tapHint || "Tap when you're ready" });
        var waiter = s.waitAsk ? Promise.race([askD.p, skipD.p]) : race(new Promise(function () {}));
        if (CFG.auto) waiter = Promise.race([waiter, sleep(6000)]);
        await waiter;
        send({ type: "tapnote", text: "" });
      }
    }
    if (my === run) { await sleep(1500); if (my === run) toIdle(); }
  }
  async function play(name) {
    wake();
    if (name === "demo") {
      await Promise.race([Promise.all([loadCare(), loadWeather()]), sleep(2500)]);
      logEv("system", { text: "Demo day started for " + CFG.name });
      return playSteps(buildDemo(), "demo");
    }
    var steps = SCRIPTS[name]; if (!steps) return;
    refreshDerived();
    return playSteps(steps, name);
  }
  function mood(pose, emo, dir) {
    wake();
    stopAll();
    send({ type: "avatar", pose: pose, emo: emo, dir: dir || "right", pos: "center", far: 0, face: "user", talking: false });
    moodT = setTimeout(toIdle, 7000);
  }

  // ------------------------------------------------------------ instructions from the dashboard
  var lastInbox = 0;
  function deliver(item) {
    wake();
    var kind = item.kind || "message", text = item.text, step;
    if (kind === "warning") step = { t: "Careful", l: wrapLines(text, 24), icon: "warn", tag: "WARNING", alert: true, pose: "alert", emo: "alert", say: "{name}, careful. " + text, hold: 3000 };
    else if (kind === "reminder") step = { t: "A reminder", l: wrapLines(text, 24), icon: "timer", tag: "REMINDER", pose: "wave", emo: "warm", say: "{name}, a quick reminder. " + text, hold: 3000 };
    else step = { t: "From your family", l: wrapLines(text, 24), icon: "person", tag: "MESSAGE", pose: "wave", emo: "happy", say: text, hold: 3000 };
    playSteps([step], "instruction");
  }
  function pollInbox() {
    api("/api/inbox?since=" + lastInbox).then(function (r) {
      (r.items || []).forEach(function (it) { lastInbox = Math.max(lastInbox, it.id); if (it.id) deliver(it); });
    }).catch(function () {});
  }
  api("/api/inbox?since=0").then(function (r) { (r.items || []).forEach(function (it) { lastInbox = Math.max(lastInbox, it.id); }); }).catch(function () {});
  setInterval(pollInbox, 1500);

  // ------------------------------------------------------------ stage sizing and the glasses look
  function fit() {
    var box = $("stagebox"), w = Math.min(box.clientWidth, 900);
    $("stage").style.width = w + "px"; $("stage").style.height = Math.round(w * 3 / 4) + "px";
    $("scaler").style.webkitTransform = "scale(" + (w / 640) + ")"; $("scaler").style.transform = "scale(" + (w / 640) + ")";
  }
  window.addEventListener("resize", fit);
  function tickClock() { var t = timeStr().replace(/\s?(AM|PM)$/i, ""); $("sbclock").textContent = t; }

  // ------------------------------------------------------------ backdrop: webcam, photo or video
  var liveStream = null, curUrl = null;
  function stopLive() { if (liveStream) { liveStream.getTracks().forEach(function (t) { t.stop(); }); liveStream = null; } }
  function showWorld(kind, src) {
    var v = $("wv"), im = $("wi");
    stopLive();
    $("worldhint").style.display = "none";
    v.style.display = kind === "video" ? "block" : "none"; im.style.display = kind === "image" ? "block" : "none";
    if (kind === "video") { v.srcObject = null; v.src = src; v.muted = true; v.loop = true; var p = v.play(); if (p && p.catch) p.catch(function () {}); }
    else { try { v.pause(); } catch (e) {} im.src = src; }
  }
  $("f-any").addEventListener("change", function (e) {
    var f = e.target.files && e.target.files[0]; if (!f) return;
    if (curUrl) { try { URL.revokeObjectURL(curUrl); } catch (x) {} }
    curUrl = URL.createObjectURL(f);
    showWorld(f.type.indexOf("video") === 0 ? "video" : "image", curUrl);
    $("msg").textContent = "Showing " + (f.name || "your file") + " behind the lens (stays on this computer).";
    e.target.value = "";
  });
  $("b-live").addEventListener("click", function () {
    if (liveStream) { stopLive(); $("wv").style.display = "none"; $("worldhint").style.display = "block"; $("msg").textContent = "Camera off. The glasses are asleep."; stopAll(); goToSleep(); return; }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { $("msg").textContent = "Camera isn't available here. Open this page from localhost or an https address."; return; }
    navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false }).then(function (st) {
      stopLive(); liveStream = st; var v = $("wv"); $("worldhint").style.display = "none"; $("wi").style.display = "none"; v.style.display = "block"; v.srcObject = st; v.play();
      $("msg").textContent = "Camera on. Move it around the room like turning your head.";
      if ($("c-start").checked) { wake(); play("demo"); }
    }).catch(function (err) {
      var name = (err && err.name) || "error";
      var why = name === "NotAllowedError" ? "The browser has blocked the camera for this page. Click the camera or lock icon in the address bar, set Camera to Allow, then reload. If you opened this inside the Claude app, open it in Chrome or Edge instead."
        : name === "NotFoundError" ? "No camera was found. Check that the webcam is plugged in and switched on."
        : name === "NotReadableError" ? "Another app is using the camera (Zoom, Teams, the Camera app, another browser tab). Close it and try again."
        : "The camera could not start.";
      $("msg").textContent = why + " [" + name + "]";
    });
  });

  // ------------------------------------------------------------ buttons
  var map = { "s-demo": "demo", "s-onboard": "onboard", "s-morning": "morning", "s-short": "short", "s-long": "long", "s-new": "newperson", "s-known": "known", "s-batt": "battery", "s-danger": "danger", "s-scared": "scared", "s-walk": "walk" };
  Object.keys(map).forEach(function (id) { if ($(id)) $(id).addEventListener("click", function () { play(map[id]); }); });
  Array.prototype.forEach.call(document.querySelectorAll("[data-mood]"), function (b) {
    b.addEventListener("click", function () { var p = b.getAttribute("data-mood").split("|"); mood(p[0], p[1], p[2]); });
  });
  $("s-stop").addEventListener("click", stopAll);
  $("b-skip").addEventListener("click", skip);
  $("catcher").addEventListener("click", skip);
  $("b-ask").addEventListener("click", function () { logEv("patient", { text: "Where is the bathroom?", sim: true }); askD.res(); });
  $("b-reset").addEventListener("click", function () { post("/api/reset", {}); $("msg").textContent = "Dashboard data cleared."; });
  $("b-look").addEventListener("click", function () { logEv("attention", { mode: "looking_around", secs: 10, sim: true }); logEv("gaze", { label: "the room around him", sim: true }); });
  $("b-straight").addEventListener("click", function () { logEv("attention", { mode: "walking_straight", secs: 10, sim: true }); });
  $("b-twirl").addEventListener("click", function () {
    wake();
    stopAll();
    send({ type: "avatar", pose: "idle", emo: null, pos: "center", far: 0, face: "user", talking: false, action: "twirl" });
  });
  $("c-glass").addEventListener("change", function (e) { $("stage").className = e.target.checked ? "glass" : ""; });
  $("c-bar").addEventListener("change", function (e) { $("fakebar").className = e.target.checked ? "" : "off"; });
  $("c-bright").addEventListener("input", function (e) { $("world").style.opacity = e.target.value / 100; });
  $("c-str").addEventListener("input", function (e) { $("scaler").style.opacity = e.target.value / 100; });
  $("c-name").addEventListener("input", function (e) { CFG.name = e.target.value.replace(/^\s+|\s+$/g, "") || "Mike"; });
  $("c-partner").addEventListener("input", function (e) { CFG.partner = e.target.value.replace(/^\s+|\s+$/g, "") || "Anna"; });
  $("c-voice").addEventListener("change", function (e) { CFG.voice = e.target.checked; if (!CFG.voice && window.speechSynthesis) speechSynthesis.cancel(); });
  $("c-auto").addEventListener("change", function (e) { CFG.auto = e.target.checked; });
  $("c-age").addEventListener("input", function (e) { CFG.age = e.target.value.replace(/[^0-9]/g, "") || "74"; });
  $("c-charm").addEventListener("change", function (e) { CFG.charm = e.target.value; });
  $("c-place").addEventListener("input", function (e) { CFG.place = e.target.value.replace(/^\s+|\s+$/g, "") || "home"; });
  $("c-weather").addEventListener("change", function (e) { if (!CFG.live) { CFG.sky = e.target.value; refreshDerived(); } });
  document.addEventListener("keydown", function (e) { if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return; if (e.key === "Enter" || e.key === " ") { e.preventDefault(); skip(); } });

  // ------------------------------------------------------------ engine badge and lens error strip
  (function () {
    var m = /Chrome\/(\d+)[\d.]*/.exec(navigator.userAgent), v = m ? parseInt(m[1], 10) : 0, el = $("engine");
    el.innerHTML = v === 74
      ? "Engine: <b class='ok'>Chromium " + navigator.userAgent.match(/Chrome\/([\d.]+)/)[1] + "</b>, the same engine as the glasses' web view."
      : "Engine: <b class='warn'>Chrome " + (v || "?") + "</b>. This is a modern browser: it can hide problems the glasses would show. Check in Chromium 74 too.";
  })();
  lens.addEventListener("load", function () {
    try {
      lens.contentWindow.onerror = function (msg, src, line) { $("errors").textContent += "Lens error: " + msg + " (" + (src || "").split("/").pop() + ":" + line + ")\n"; };
    } catch (e) {}
    send({ type: "config", hint: "Say “Gogo” to ask" });
    if (sleeping) send({ type: "power", on: false });
  });

  refreshDerived(); fit(); tickClock(); setInterval(tickClock, 15000); setTimeout(fit, 200);
  loadCare().then(loadWeather);
})();
