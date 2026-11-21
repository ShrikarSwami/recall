# lens/: the UI on the glasses (frontend devs own this)

`lens/index.html` + `lens.css` + `lens.js` is **exactly what the wearer sees**. The glasses app loads it
full-screen in a WebView from the hub (`http://<hub>:9100/lens/`), and the simulator (`sim/`) shows the same
file in a 640×480 iframe. Edit here, reload the simulator, done. No build step.

## Try it

1. Open `../sim/index.html` in Chrome (double-click works, or `python3 -m http.server 9200` from the repo root →
   `http://localhost:9200/sim/`).
2. Use the buttons on the right to push every state onto the lens (see "States" below).
3. With the real hub running, switch the simulator to **Live hub** to see real answers.

## The screen

- **640 × 480 px at 160 dpi.** CSS px = device px. The body is fixed at 640×480; don't make it responsive.
- **Black (#000) is see-through.** Lit pixels float over the real world, and bright areas cost battery and
  hide the world. Keep large areas black. No filled panels or backgrounds.
- **The M6 is a green waveguide** (a full-colour module exists). Colour can't carry meaning: use text, weight
  and size. The simulator's "Green waveguide" toggle shows the real look.
- **Top 40 px are covered by the glasses' own status bar** (clock, BT, Wi-Fi, battery), which apps can't hide.
  Keep `#safe-top` empty.
- **Readability:** body text ≥ 24 px, titles ≥ 30 px, short lines (≤ ~34 chars), 3 lines max. The hub already
  wraps `lines` to ≤ 34 chars × 3.
- **The pinned hint (`#hint`, bottom-left) must always be visible.** It's the "brand-new user every time" rule:
  someone who forgot everything should still know what to do.

## Browser: Chrome 74 (Android 9 WebView). These will break on the glasses:

| Don't use | Use instead |
|---|---|
| `a?.b`, `a ?? b` | `a && a.b`, `a != null ? a : b` |
| flex/grid `gap` on flex containers | margins on children |
| `:is()`, `:where()`, `:has()`, `aspect-ratio`, `backdrop-filter`, container queries | plain selectors, explicit sizes |
| ES modules from CDNs, frameworks needing a bundler | plain `<script>`; if you want a framework, vendor a UMD build into `lens/vendor/` |
| `structuredClone`, `Array.prototype.at`, `replaceAll` | manual equivalents |

Debug on the real glasses: with the glasses on USB, open `chrome://inspect` on the laptop → the Lucia WebView.

## Messages the lens renders

The lens is display-only. Input (taps, mic, camera) goes from the glasses app straight to the hub.

```js
{"type":"config", "hint":"Say \"Lucia\" to ask", "app":"Lucia", "patient":"Somya", "now":<epoch ms>, "tz":-300}
{"type":"state",  "value":"idle" | "listening" | "thinking"}
{"type":"card",   "title":"Abhiram", "lines":["This is Abhiram. He's on","your team."], "ttl_ms":8000, "intent":"..."}
{"type":"clear"}
{"type":"conn",   "value":true | false}
```

`intent` lets you style cards differently. It's set as a class on `#card` (`intent-distress` etc.):

| intent | when | design note |
|---|---|---|
| `greeting` | glasses just put on | warm, orient them: who/where |
| `proactive_intro` | a known face walked up, nobody asked | the wow moment; make the name prominent |
| `who_is_this` / `who_is` | "who is this?" | name big, one line of relationship |
| `kb:person` `kb:place` `kb:patient` `kb:faq` | answer from the knowledge base | standard card |
| `time` | "what day is it?" | big time/day |
| `distress` | "I want to go home", "I'm scared" | calm and reassuring, never alarming |
| `unknown` / `freeform` | off-script question; the model answered | slightly dimmer, it's less certain |

The clock must use the hub's `now`/`tz` (already handled in `lens.js`): the glasses ship set to China time.

## States to design (all reachable from the simulator)

idle (hint + clock only) · listening · thinking · answer card · proactive intro · greeting · distress ·
unknown person ("I don't think we've met them yet") · long answer (3-line overflow) · disconnected.
