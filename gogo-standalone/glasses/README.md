# Lucia glasses lens + simulator

| Folder | What |
|---|---|
| `lens/` | **The page the M6 shows** (640x480, black = see-through). Plain HTML/CSS/JS, written for Chrome 74. Drop-in for the repo's `lens/`. |
| `sim/` | A browser simulator: your webcam (or a photo/video) behind the lens, scripted moments, glasses-look filter. Drives the lens with the same messages the hub will send. |

## Run it in the glasses' engine

Double-click `..\..\chromium74\Run Lucia simulator in Chrome 74.bat`. It starts a small local server and opens the simulator in
Chromium 74.0.3729 (the version of the M6's Android System WebView). The badge at the top should say **Chromium 74.0.3729.0**.
Click **Live camera**, allow your webcam, then press **Wake up, new day**. Only use that browser for this page.

## Lens messages (what the hub will send)

```
{"type":"config",  "hint":"Say \"Lucia\" to ask", "now":<epoch ms>, "tz":-300}
{"type":"card",    "title":"Good morning", "lines":["You're safe"], "icon":"shield", "tag":"SAFE", "alert":false, "ring":false, "ttl_ms":0}
{"type":"clear"}
{"type":"avatar",  "pose":"idle|wave|point|walk|sleepy|calm|alert|cheer", "emo":"warm|happy|proud|curious|concerned|sleepy|calm|alert",
                   "pos":"left|center|right", "far":0..1, "face":"user|away", "dir":"left|right", "talking":true}
{"type":"avatar",  "action":"twirl"}        (the Lucia twirl: wave, hop, spin all the way round, bow, wave: about 4 seconds)
{"type":"arrows",  "value":"left|right|both|"}
{"type":"ring",    "phase":"in|out", "label":"Breathe in..."}
{"type":"tapnote", "text":"Tap when you're ready"}
{"type":"battery", "on":true, "pct":15}
```

## Chrome 74 rules for the lens (each one verified in real Chromium 74.0.3729.0)

| Not supported | Use instead |
|---|---|
| CSS `inset` | `top/left/right/bottom` |
| `gap` on flex containers | margins on the children |
| CSS `min()`, `max()`, `clamp()`, `aspect-ratio`, `:is()` | fixed sizes, `calc()` |
| `?.` and `??` | `a && a.b`, `a != null ? a : b` |
| `replaceAll`, `Array.at` | manual code |

Supported and used: flexbox, CSS variables, transforms, keyframe animations, canvas 2D, inline SVG, `async`/`await`, `mix-blend-mode`.

## The squirrel

`../tools/squirrel_sdf.py` models it in 3D (and exports `../assets/squirrel.glb`); `../tools/bake_sprites.py` renders 54 flat sprites from five
angles (three are mirrored). The lens only plays images, so the glasses do no 3D work. Re-bake after changing the model, then copy
`../assets/squirrel_sheet.png` and `squirrel_sheet.json` (as `squirrel_map.js`) into `lens/`.

## Not verified yet (needs the real glasses)

Brightness and readability on the real waveguide, field of view, frame rate and battery on the real chip, the hub driving the lens,
and the Atkinson Hyperlegible font (not bundled yet: `lens/fonts/` is empty, so Chrome falls back to Arial on a PC and Roboto on the M6).
