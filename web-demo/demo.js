/* Go-go web demo: drives the real lens page (lens/, postMessage mode) and shares a store with the caregiver
   page (caregiver/, through mock-api.js). Answers come from the same prepared knowledge the glasses use
   (brain/mock-kb.js, generated from knowledge/*.md). Plain ES5 so it runs anywhere. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var lens = $("lens"), KB = window.MockBrain.kb, Brain = window.MockBrain;
  var APP = KB.app || "Go-go", PATIENT = (KB.patient || "Somya").split(" ")[0], CARER = KB.caregiver || "Shrikar";
  var PLACE = "City Tech, Downtown Brooklyn";
  var OFFER_HOW = 'Nod or say "yes" · shake or say "no"';
  var GROCERY = ["whole milk", "ground tofu", "bananas"];
  var DAY = [["08:00", "Breakfast"], ["09:00", "Team check-ins"], ["10:00", "SDK and hardware workshop"], ["11:00", "Pitch workshop"],
    ["12:30", "Lunch"], ["14:00", "Submissions close"], ["14:15", "Judging"], ["15:45", "Finalists announced"], ["16:00", "Finalist demos"],
    ["16:45", "Dr. Dai's talk"], ["17:30", "Awards"], ["18:00", "Hardware return"]];
  var on = false, offer = null, talkTimer = null, gen = 0;

  // ------------------------------------------------------------ shared store (read by caregiver/mock-api.js)
  var G = window.GogoDemo = {
    events: [], data: null,
    live: { location: "seat", step: "", lastLucia: "", lensSeen: 0, scene: "idle" },
    add: function (type, kw) {
      var ev = { id: this.events.length + 1, ts: Date.now() / 1000, type: type };
      for (var k in kw) ev[k] = kw[k];
      this.events.push(ev);
      if (type === "lucia") this.live.lastLucia = kw.text;
      return ev;
    },
    key: function (k) { var label = run(k); return label ? { ok: true, label: label } : { ok: false }; },
    instruct: function (text) { if (on) say(text, "From family", "manual"); }
  };
  setInterval(function () { if (on) G.live.lensSeen = Date.now() / 1000; }, 1000);
  G.live.step = "";

  // ------------------------------------------------------------ lens + voice
  function lensMsg(m) { lens.contentWindow.postMessage(m, "*"); }
  function wrap(text) {
    var words = text.split(" "), lines = [], cur = "";
    words.forEach(function (w) { if ((cur + " " + w).trim().length > 34) { lines.push(cur.trim()); cur = w; } else cur += " " + w; });
    if (cur.trim()) lines.push(cur.trim());
    return lines.slice(0, 3);
  }
  function talking(v) { lensMsg({ type: "avatar", talking: v }); }
  function say(speech, title, intent, opts) {
    opts = opts || {};
    var my = ++gen, card = opts.card || speech;
    if (window.speechSynthesis) speechSynthesis.cancel();
    lensMsg({ type: "state", value: "idle" });
    lensMsg({ type: "card", title: title, lines: wrap(card), intent: intent, prompt: opts.prompt || "",
              ttl_ms: Math.max(6000, 450 * speech.split(" ").length + 3000) + (opts.prompt ? 10000 : 0) });
    talking(true);
    var done = function () { if (my === gen) talking(false); };
    if (talkTimer) clearTimeout(talkTimer);
    if ($("sound").checked && window.speechSynthesis) {
      var u = new SpeechSynthesisUtterance(speech); u.rate = 0.95; u.onend = done; speechSynthesis.speak(u);
      talkTimer = setTimeout(done, 380 * speech.split(" ").length + 4000);
    } else talkTimer = setTimeout(done, 330 * speech.split(" ").length + 600);
    G.add("lucia", { text: speech });
  }
  function think(fn) { lensMsg({ type: "state", value: "thinking" }); setTimeout(fn, 450); }
  function stop() {
    gen++; if (window.speechSynthesis) speechSynthesis.cancel();
    lensMsg({ type: "clear" }); lensMsg({ type: "avatar", talking: false, perk: true });
  }
  function power(v) {
    on = v; lensMsg({ type: "power", on: v });
    if (!v) { stop(); G.live.lensSeen = 0; }
  }
  function phone(text) {
    $("phone-text").textContent = text; $("phone").className = "on";
    setTimeout(function () { $("phone").className = ""; }, 6500);
  }
  function stamp() {
    var d = new Date();
    return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }) + " · " + PLACE;
  }

  // ------------------------------------------------------------ people + yes/no
  function factsFor(id) {
    return KB.entries.filter(function (e) {
      return e.scope === "person" && e.subject === id && !/^(who('s| is) (this|that)|how do i know)/i.test(e.questions[0]) && e.answer;
    });
  }
  function meet(id) {
    if (!on) power(true);
    Brain.see(id);
    var p = KB.people[id], first = p.first;
    G.add("gaze", { label: first });
    offer = { id: id, i: 0 };
    say(Brain.intro(id) + " Want to hear more about " + first + "?", first, "proactive_intro",
        { card: Brain.intro(id), prompt: "Hear more about " + first + "?\n" + OFFER_HOW });
  }
  function answerOffer(yes) {
    if (!offer) { G.add("patient", { text: yes ? "Yes." : "No." }); return say(yes ? "Okay." : "Okay.", APP, "offer_no"); }
    G.add("patient", { text: yes ? "Yes, tell me more." : "No thanks." });
    if (!yes) { offer = null; return say("Okay.", APP, "offer_no"); }
    var f = factsFor(offer.id), first = KB.people[offer.id].first;
    if (!f.length || offer.i >= Math.min(3, f.length)) { offer = null; return say("That's all I know about " + first + " for now.", first, "offer_yes"); }
    var fact = f[offer.i++].answer, more = offer.i < Math.min(3, f.length);
    say(fact + (more ? " Want to hear more?" : ""), first, "offer_yes", { card: fact, prompt: more ? "Hear more about " + first + "?\n" + OFFER_HOW : "" });
    if (!more) offer = null;
  }

  // ------------------------------------------------------------ the demo moments
  function nextToday() {
    var d = new Date(), now = d.getHours() * 60 + d.getMinutes();
    for (var i = 0; i < DAY.length; i++) {
      var hm = DAY[i][0].split(":"), t = +hm[0] * 60 + +hm[1];
      if (t >= now) {
        var mins = t - now, h = +hm[0] % 12 || 12, at = h + (hm[1] === "00" ? "" : ":" + hm[1]);
        var after = DAY.slice(i + 1, i + 2).map(function (x) { var p = x[0].split(":"); return x[1] + " at " + (+p[0] % 12 || 12) + (p[1] === "00" ? "" : ":" + p[1]); });
        return "Next is " + DAY[i][1] + " at " + at + (mins < 90 ? ", in about " + mins + " minutes" : "") + "." + (after.length ? " After that, " + after.join(" and ") + "." : "");
      }
    }
    return "That's everything for today. Tomorrow starts with breakfast at 8.";
  }
  function run(k) {
    if (k === "s") { power(true); offer = null; lensMsg({ type: "avatar", action: "greet" });
      say("Welcome! I'm " + APP + ", here to help you remember. Look at someone, and I'll tell you who they are.", "Welcome", "greeting", { card: "I'm here to help you remember." });
      return "Start: welcome"; }
    if (k === "b") { power(false); return "Blank: lens off"; }
    if (k === "x") { stop(); return "Stop talking"; }
    if (!on) power(true);
    if (k === "g") { G.add("system", { text: "Arrived at the grocery store" }); offer = null;
      say("You're at the grocery store. You need: " + GROCERY.slice(0, -1).join(", ") + " and " + GROCERY[GROCERY.length - 1] + ".", "The grocery store", "arrival");
      return "Grocery list"; }
    if (k === "c") { offer = null; G.add("patient", { text: "What's next today?" }); think(function () { say(nextToday(), "Coming up", "schedule"); }); return "Today's schedule"; }
    if (k === "f") {
      offer = null;
      var text = APP + ": WARNING: " + PATIENT + " may have fallen. Please check on them urgently! · " + stamp();
      G.add("alert", { text: "Possible fall detected" });
      G.add("alert", { text: "Text sent to caregiver: " + text });
      phone(text.replace(APP + ": ", ""));
      stop();
      setTimeout(function () { say(PATIENT + ", are you okay? I've let " + CARER + " know. Help is on the way.", "Are you okay?", "fall"); }, 300);
      return "Fall alert";
    }
    return "";
  }
  function ask(text) {
    text = String(text || "").trim(); if (!text) return;
    if (!on) power(true);
    G.add("patient", { text: text });
    var q = text.replace(/^\s*(hey\s+)?(go-?go|go go)[\s,.!?-]*/i, "");
    if (/^(yes|yeah|yep|sure|ok(ay)?|please)\b/i.test(q) && offer) return answerOffer(true);
    if (/^(no|nope|nah|not now)\b/i.test(q) && offer) return answerOffer(false);
    if (/^(what'?s|what is) (next|on (my|the) (schedule|calendar))|what'?s (on )?today/i.test(q)) return think(function () { say(nextToday(), "Coming up", "schedule"); });
    offer = null;
    think(function () {
      var r = Brain.answer(q);
      if (r.intent === "speech_stop") return stop();
      var speech = r.speech;
      if (r.intent === "freeform") speech = "I'm not sure about that one. Should I let " + CARER + " know?";
      if (r.alert) { var t = APP + ": " + r.alert + " · " + stamp(); G.add("alert", { text: "Text sent to caregiver: " + t }); phone(r.alert + " · " + stamp()); }
      say(speech, r.title || APP, r.intent);
    });
  }

  // ------------------------------------------------------------ wiring
  function fit() {
    var box = $("lens-box"), s = box.clientWidth / 640;
    $("lens-scale").style.transform = "scale(" + s + ")";
  }
  window.addEventListener("resize", fit); fit();
  lens.addEventListener("load", function () {
    lensMsg({ type: "config", hint: KB.hint || 'Say "Go-go" or hold right side', now: Date.now(), tz: -new Date().getTimezoneOffset() });
    power(false);
  });
  Array.prototype.forEach.call(document.querySelectorAll("[data-k]"), function (b) { b.addEventListener("click", function () { run(b.getAttribute("data-k")); }); });
  Array.prototype.forEach.call(document.querySelectorAll("[data-person]"), function (b) { b.addEventListener("click", function () { meet(b.getAttribute("data-person")); }); });
  Array.prototype.forEach.call(document.querySelectorAll("[data-say]"), function (b) { b.addEventListener("click", function () { answerOffer(b.getAttribute("data-say") === "yes"); }); });
  $("ask").addEventListener("submit", function (e) { e.preventDefault(); ask($("ask-text").value); $("ask-text").value = ""; });
  ["Go-go, where am I?", "What day is it?", "Who is Abhiram?", "Say that again", "I want to go home"].forEach(function (q) {
    var b = document.createElement("button"); b.type = "button"; b.textContent = q;
    b.addEventListener("click", function () { ask(q); }); $("examples").appendChild(b);
  });
  document.addEventListener("keydown", function (e) {
    var tag = (e.target && e.target.tagName) || "";
    if (e.metaKey || e.ctrlKey || e.altKey || tag === "INPUT" || tag === "TEXTAREA") return;
    var k = (e.key || "").toLowerCase();
    if ("sgcfxb".indexOf(k) >= 0 && k.length === 1) { e.preventDefault(); run(k); }
  });
})();
