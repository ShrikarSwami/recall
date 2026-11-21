/* Offline stand-in for hub/lucia/brain.py so the simulator works with no backend.
   Simplified on purpose: same intents and wording rules, rougher matching.
   Real answers come from window.MOCK_KB (generated from knowledge/*.md). */
(function () {
  "use strict";
  var KB = window.MOCK_KB || { entries: [], people: {}, places: {}, patient: "Somya", caregiver: "Shrikar", app: "Lucia" };

  var DISTRESS = /\b(go(ing)? home|want (to go )?home|take me home|scared|afraid|i('m| am) lost|where is everyone|help me|i('m| am) confused)\b/i;
  var TIME = /\bwhat (time|day)\b|\bwhat('s| is) the date\b|\bwhat year\b|\btoday's date\b/i;
  var WHO_THIS = /\bwho('s| is| are)? (this|that|he|she|they|in front of me|next to me)\b|\bwho am i talking to\b|(?<!how )\bdo i know (him|her|them|this)\b/i;
  var PRON = /\b(he|she|him|her|his|hers|they|them|their)\b|\b(this|that) (person|guy|girl|man|woman|lady)\b/gi;

  function norm(s) {
    return s.toLowerCase().replace(/[’']/g, "'").replace(/\bwhat's\b/g, "what is").replace(/\bwhere's\b/g, "where is")
      .replace(/\bwho's\b/g, "who is").replace(/[^a-z0-9' ]+/g, " ").replace(/\s+/g, " ").trim();
  }
  function canon(s, names) {
    var t = " " + norm(s) + " ";
    (names || []).forEach(function (n) { if (n) t = t.replace(new RegExp("\\b" + n.toLowerCase() + "('s)?\\b", "g"), "X"); });
    return t.replace(PRON, "X").replace(/\b(lucia|please|can|you|tell|me|hey|um)\b/g, " ").replace(/\s+/g, " ").trim();
  }
  function score(a, b) {  // token Dice similarity, 0..100
    var A = a.split(" "), B = b.split(" "), hit = 0;
    A.forEach(function (w) { if (B.indexOf(w) >= 0) hit++; });
    return (200 * hit) / (A.length + B.length || 1);
  }
  function wrap(text) {
    var words = text.split(" "), lines = [], cur = "";
    words.forEach(function (w) { if ((cur + " " + w).trim().length > 34) { lines.push(cur.trim()); cur = w; } else cur += " " + w; });
    if (cur.trim()) lines.push(cur.trim());
    return lines.slice(0, 3);
  }
  function card(speech, title, intent) { return { type: "card", title: title, lines: wrap(speech), intent: intent, ttl_ms: 9000, speech: speech }; }

  var state = { inView: null, inViewAt: 0, strangerAt: 0, topic: null };

  function personNamed(t) {
    var n = " " + norm(t) + " ", found = null;
    Object.keys(KB.people).forEach(function (id) {
      var p = KB.people[id];
      [p.name, p.first].concat(p.aliases || []).forEach(function (x) {
        if (x && new RegExp("\\b" + x.toLowerCase() + "\\b").test(n)) found = id;
      });
    });
    return found;
  }
  function intro(id) {
    var p = KB.people[id];
    for (var i = 0; i < KB.entries.length; i++) {
      var e = KB.entries[i];
      if (e.subject === id && /^who('s| is) (this|that)/i.test(e.questions[0])) return e.answer;
    }
    return p.intro || "This is " + p.first + ".";
  }
  function inView() { return Date.now() - state.inViewAt < 15000 ? state.inView : null; }

  function answer(text) {
    var t = text.trim();
    if (DISTRESS.test(t)) {
      var r = card("You're safe, " + KB.patient + ". " + KB.caregiver + " knows where you are, and I'm letting him know now.", "You're safe", "distress");
      r.alert = KB.patient + ' said: "' + t + '"';
      return r;
    }
    if (TIME.test(t)) {
      var d = new Date();
      return card("It's " + d.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" }) +
        ". It's about " + d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }) + ".", d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }), "time");
    }
    var named = personNamed(t);
    if (WHO_THIS.test(t) && !named) {
      var v = inView();
      if (v) { state.topic = v; return card(intro(v), KB.people[v].first, "who_is_this"); }
      if (Date.now() - state.strangerAt < 15000) return card("I don't think we've met them yet. It's okay to ask their name.", "Someone new", "who_is_this");
      return card("I don't see anyone in front of you right now.", "No one here", "who_is_this");
    }
    var person = named || ((PRON.test(t) && (PRON.lastIndex = 0, true)) ? (inView() || state.topic) : null);
    PRON.lastIndex = 0;
    if (named) state.topic = named;
    var names = person ? [KB.people[person].name, KB.people[person].first].concat(KB.people[person].aliases || []) : [];
    var q = canon(t, names), best = null, bestScore = 0;
    KB.entries.forEach(function (e) {
      if (e.scope === "person" && e.subject !== person) return;
      if (e.scope === "place" && e.subject !== KB.currentPlace) return;
      var en = e.scope === "person" ? names : [];
      e.questions.forEach(function (ph) {
        var s = score(q, canon(ph, en)) + (e.scope === "person" ? 4 : 0);
        if (s > bestScore) { bestScore = s; best = e; }
      });
    });
    if (best && bestScore >= 60) {
      var title = best.scope === "person" ? KB.people[best.subject].first : best.scope === "place" ? "Where you are" : best.scope === "patient" ? KB.patient : KB.app;
      if (best.scope === "person") state.topic = best.subject;
      return card(best.answer, title, "kb:" + best.scope);
    }
    return card("(Mock) Off-script: the live hub would ask the local model here.", KB.app, "freeform");
  }

  window.MockBrain = {
    answer: answer,
    see: function (id) { if (id) { state.inView = id; state.inViewAt = Date.now(); } else state.strangerAt = Date.now(); },
    intro: intro,
    introCard: function (id) { return card(intro(id), KB.people[id].first, "proactive_intro"); },
    greeting: function () {
      var pl = KB.places[KB.currentPlace] || {};
      return card("Hi " + KB.patient + "." + (pl.name ? " You're at " + pl.name + "." : "") + ' Say "' + KB.wake + '" if you need anything.', "Hi " + KB.patient, "greeting");
    },
    kb: KB
  };
})();
