/* Stand-in for the care server's /api/* so the caregiver page runs as a static site (Vercel demo).
   Inside the demo page it shares one store with the glasses (window.parent.GogoDemo); opened on its own
   it keeps a small in-memory store. Loaded before the dashboard's own script. */
(function () {
  "use strict";
  var local = null;
  function S() {   // the demo page's shared store when embedded (it may be created after this frame loads)
    try { if (window.parent !== window && window.parent.GogoDemo) return window.parent.GogoDemo; } catch (e) {}
    return local;
  }
  if (true) {
    local = { events: [], live: { location: "seat", step: "", lastLucia: "", lensSeen: 0, scene: "idle" }, data: null,
      add: function (type, kw) { var ev = { id: this.events.length + 1, ts: Date.now() / 1000, type: type }; for (var k in kw) ev[k] = kw[k]; this.events.push(ev); return ev; },
      key: function () { return { ok: false }; }, instruct: function () {} };
  }
  var store;
  function json(obj) { return Promise.resolve(new Response(JSON.stringify(obj), { headers: { "Content-Type": "application/json" } })); }
  function data() {
    if (store.data) return Promise.resolve(store.data);
    return window.__realFetch("../data.json").then(function (r) { return r.json(); }).then(function (d) { store.data = d; return d; });
  }
  window.__realFetch = window.fetch.bind(window);
  window.fetch = function (path, opts) {
    var url = String(path);
    if (url.indexOf("/api/") !== 0) return window.__realFetch(path, opts);
    var body = {};
    try { body = opts && opts.body ? JSON.parse(opts.body) : {}; } catch (e) {}
    var p = url.split("?")[0];
    store = S();
    return data().then(function (d) {
      if (p === "/api/state") {
        var live = {}; for (var k in store.live) live[k] = store.live[k];
        live.lensOnline = Date.now() / 1000 - (store.live.lensSeen || 0) < 6;
        return json({ profile: d.profile, goals: d.goals, places: d.places, live: live, now: Date.now() / 1000 });
      }
      if (p === "/api/events") {
        var since = +(url.split("since=")[1] || 0);
        return json({ events: store.events.filter(function (e) { return e.id > since; }) });
      }
      if (p === "/api/profile" || p === "/api/goals" || p === "/api/places") {
        var key = p.split("/").pop(); d[key] = body[key] || body;
        store.add("system", { text: "Care plan updated: " + key });
        return json({ ok: true });
      }
      if (p === "/api/instruct") {
        store.add("instruction", { text: body.text, kind: body.kind || "message", by: body.by || "Family dashboard" });
        store.instruct(body.text);
        return json({ ok: true });
      }
      if (p === "/api/demo") return json(store.key(String(body.key || "")));
      if (p === "/api/weather") return json({ ok: false });
      return json({ ok: true });
    });
  };
})();
