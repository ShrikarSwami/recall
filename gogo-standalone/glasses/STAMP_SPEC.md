# GOGO stamps: spec for generating the illustrations

Every card on the glasses can carry one small **postage stamp**: a perforated border around a flat illustration, with a one- or two-word label. This file says exactly what the stamps are, where each is used, and what the artwork must be so it works on the M6 glasses (Chrome 74, 640×480, single-colour green waveguide).

## 1. The stamp itself (fixed, do not redesign)

| Part | Spec |
|---|---|
| Size on the lens | **84 × 98 px**, tilted **−3°** (like a stamp stuck on at a slight angle). The stamp is built in a **96 × 112** drawing space. |
| Border | 8 units thick, solid bright green, with **perforations**: semicircle bites (radius 3.6) every 12 units along the top and bottom, every 16 units along the sides. |
| Inner frame | A thin line (1.2 units) in bright green inside the border, 74 × 90 units, like the double frame on the reference stamps. |
| Panel | 80 × 96 units, **black** (black = see-through on the glasses). |
| Illustration area | **70 × 70 units**, at x 13, y 12 inside the stamp. Keep real content inside a 62 × 62 centre (4 units of air on every side). |
| Label | Bottom of the panel, **9 px bold, UPPERCASE**, bright green, centred. Up to 8 characters at normal width; longer labels are squeezed to fit (max about 11 characters). The label is **not part of the artwork**. |
| Variants | **Normal** (black panel, green art). **Alert** (inverted: bright-green panel, dark art), used only for warnings. |

The perforated border, frame and label are drawn by the lens code. **You only supply the 70 × 70 illustration.**

## 2. Colours: only these four tones (plus line colour)

The glasses can only show brightness of green. Use exactly these (the lens sets them; the artwork refers to them by class, see section 4).

| Role | Normal stamp | Alert stamp |
|---|---|---|
| **k1** bright (focal subject, highlights) | `#00FF50` | `#021A0A` |
| **k2** mid | `#00B83A` | `#0A5A26` |
| **k3** dim (ground, shadows, background shapes) | `#006B2A` | `#12803A` |
| **k4** contrast (eyes, details cut into k1/k2, the panel colour) | `#000000` | `#00FF50` |
| **kl** line (stroke 2.4, round caps) | same as k1 | same as k1 |

Do not use any other colour, gradient, transparency, blur, shadow or texture.

## 3. Style brief

- **Flat vector postage-stamp illustration**: simple geometric shapes, bold silhouettes, one clear subject, a dim ground or background shape to give depth. Reference: the two vintage stamp images shared (scalloped border, dark panel, 3-tone flat shapes) and the flat caregiving illustration (people, furniture, soft rounded shapes).
- **Warm and calm**, never scary or clinical. Friendly rounded forms, small simple faces (two dots, a small smile), no sharp or aggressive shapes.
- **Readable in one second** by an older person: one focal subject, big shapes, high contrast between k1 and the black panel.
- Characters are drawn from the front or side, upper body or full figure, no text inside the art.
- **Gogo the squirrel** may appear as a small guide in a scene where it helps (optional, keep it tiny and simple).

## 4. Technical contract for each illustration (what makes it work on the glasses)

| Requirement | Why |
|---|---|
| **One SVG per stamp**, `viewBox="0 0 70 70"`, no width/height attributes, file named `s-<id>.svg` | The lens places it into the stamp. |
| Only `<path>`, `<circle>`, `<ellipse>`, `<rect>`; **no** `<text>`, `<image>`, gradients, filters, masks, clipPaths, `<style>` blocks, `style=""` attributes, opacity or `fill-opacity` | Chrome 74 + cheap to draw + exact colours. |
| Colour **only through classes**: `class="k1"`, `k2`, `k3`, `k4` for filled shapes; `class="kl"` for a bright line (no fill); `class="kl4"` for a contrast line | The lens swaps the colours for the alert variant. |
| **Smallest detail 2.5 units, thinnest gap 2.5 units**; lines are `kl` (2.4) only | The art is shown at about 61 × 61 px; thinner details disappear. |
| At most about **25 shapes** and **2 KB** per file | Fast to load and draw on the glasses' chip. |
| Lit area (k1 + k2) at most about **50 %** of the 70 × 70 area; keep at least a quarter of it black | Bright pixels cost battery and block the wearer's view. |
| Subject centred, **4 units of air** around it; ground/hill shapes may run to the edge | The inner frame crops anything outside. |
| No faces with fine detail (eyes = two dots `k4`, mouth = one `kl4` curve) | Too small to read otherwise. |

Format example (this is the existing "person" stamp):

```svg
<svg viewBox="0 0 70 70" xmlns="http://www.w3.org/2000/svg">
  <path class="k3" d="M0 70 V58 Q35 51 70 58 V70Z"/>
  <path class="k2" d="M10 70 C10 52 22 46 35 46 C48 46 60 52 60 70Z"/>
  <circle class="k2" cx="35" cy="31" r="12"/>
  <path class="k1" d="M22 29 C22 13 48 13 48 29 C45 21 25 21 22 29Z"/>
  <circle class="k4" cx="30" cy="30" r="1.6"/><circle class="k4" cx="40" cy="30" r="1.6"/>
</svg>
```

If an image (PNG) is the only option: 280 × 280 px, transparent background, **only the four hex colours above, no anti-aliased blends between them**, and I will convert it. SVG is strongly preferred.

## 5. Every stamp, where it appears, and what the artwork shows

Status: **drawn** = a first version exists in the lens (Gemini can improve it); **line icon** = still a plain line icon, needs a real scene; **unused** = drawn but not in the current flow.

| ID | Used where (label on the stamp) | Illustration brief | Variant | Status |
|---|---|---|---|---|
| `shield` | "I'm with you" (WITH YOU), "You're safe" (SAFE), "You made it" (MADE IT), "All clean" (CLEAN), "Well done" (DONE), reassurance after a scare (SAFE), battery thanks (THANKS) | A friendly protective shield with a heart; a small guide (Gogo) beside it is optional. Feels like "you are safe and looked after". | Normal | drawn |
| `person` | "You're Mike" (YOU); someone new (HELLO, NEW FRIEND); family (FAMILY); dashboard message (MESSAGE) | A warm portrait of an **elderly person**: white hair and beard, cardigan, kind face. Needs a male version (Mike) and, ideally, a female version and a neutral "visitor" version. | Normal | drawn (male only) |
| `friends` | "You're here, with your friends" (FRIENDS) | A small group of 3 friendly people close together, one slightly in front, a small star or sparkle. Feels like a gathering. | Normal | drawn |
| `sun` | Weather, when sunny (label shows the temperature, e.g. 46°F) | A big simple sun over a gentle hill. | Normal | drawn |
| `moon` | Weather, when clear at night; "after a nap" (REST) | A crescent moon with two small stars over a hill. | Normal | drawn |
| `cloud` | Weather, when cloudy, foggy or snowy | A soft cloud with the sun peeking behind it. | Normal | drawn |
| `rain` | Weather, when rainy or stormy | A cloud with slanted rain lines; an umbrella is optional. | Normal | drawn |
| `bag` | "Your bag" (SAFE) | A backpack standing on the floor, straps and a front pocket. | Normal | drawn |
| `timer` | "Today" (TODAY); dashboard reminder (REMINDER) | A friendly clock face with a bright wedge showing time passing. | Normal | drawn |
| `drop` | "Let's freshen up" (FRESH UP), "Turn the tap on" (WASH 1), "Rinse" (WASH 3), "First: a glass of water" (FIRST) | A single big water drop with a highlight; for washing, a tap with running water is welcome. Needs **two** versions: drop (water) and tap-with-water (washing). | Normal | drawn (drop only) |
| `bath` | "Where to?" (ASK ME), "The bathroom" (THIS WAY), "Step 4 of 4" (STEP 4) | A bathroom sink with a tap and mirror, a drop falling from the tap. Optionally a simple restroom door. | Normal | drawn |
| `chair` | "Step 1: stand up and step back" (STEP 1), "Your seat" (SIT), "back to your seat" (STEP 3) | A comfy armchair seen from the front with a cushion. A second version with a person standing up from it is welcome. | Normal | drawn |
| `gate` | "Step 2: head to the gate" (STEP 2), return route (STEP 1) | An open garden-style gate with two posts and a path leading through it. | Normal | drawn |
| `forward` | "Step 3: go through the gate" (STEP 3), return route (STEP 2) | A clear **right-pointing** arrow on a path. Needs a left and an up version too (below). | Normal | drawn |
| `hands` | "Dry your hands" (WASH 4) | A towel hanging on a rail; hands drying on it would be even better. | Normal | drawn |
| `soap` | not used yet (could be "Rub, rub, rub", WASH 2) | A soap bar with bubbles. | Normal | unused |
| `home` | "At home" (HOME), "This is the kitchen" (KITCHEN) | A small house with a door and two windows. A kitchen version (a kettle or a table) is welcome. | Normal | drawn |
| `eye` | "Look around" (LOOK) | A big friendly eye over a hill, with a bright iris and a sparkle. | Normal | drawn |
| `warn` | Danger and dashboard warnings: "Careful" (CAREFUL, WARNING) | A rounded warning triangle with an exclamation mark. Calm, not frightening. A stove or stairs version is welcome. | **Alert** | drawn |
| `back` | "Step back" (SLOWLY) | A clear **left-pointing** arrow on a path. | **Alert** | drawn |
| `up` | not used yet (straight ahead) | An arrow pointing straight ahead on a road. | Normal | unused |
| `smile` | "Ready?" (READY), "Say hello" (SAY), "Let's walk" (COME ON) | Scene of two people greeting, or a waving hand and a speech bubble. Needs a real scene (currently a plain face). | Normal | line icon |
| `cup` | "Next: breakfast or tea" (NEXT) | A cup of tea with steam on a table. | Normal | line icon |
| `battery` | "I'm getting sleepy" (15%) | A low battery with one bar, and Gogo yawning is welcome. | Normal | line icon |
| `glasses` | "Take me off" (STEP 1) | A pair of glasses being lifted off a face by two hands. | Normal | line icon |
| `plug` | "Find the charger" / "Plug it in" (STEP 2, STEP 3) | A cable plugging into a socket, or into the glasses. | Normal | line icon |

**Arrow directions needed:** `forward` (right), `back` (left), `up` (straight). The `gate` stamps are also reused for "turn left" and "turn right" later, so a left and right gate would help.

**Not a stamp:** the first card, "Hi, I'm Gogo", has no stamp (the big squirrel is the picture). The GOGO splash is a separate logo.

## 6. Prompt to give Gemini (copy and paste)

> Design a flat vector **postage-stamp illustration** for a smart-glasses app for people living with dementia. Output **one SVG** with `viewBox="0 0 70 70"` and no width or height. Use **only** `<path>`, `<circle>`, `<ellipse>`, `<rect>`. Colour **only with classes**: `k1` (brightest, the main subject), `k2` (mid tone), `k3` (dim tone for ground and background shapes), `k4` (contrast detail such as eyes), `kl` (a 2.4-unit bright line, no fill), `kl4` (a contrast line). No gradients, filters, masks, opacity, text or inline styles. Style: simple geometric flat shapes, warm and calm, one clear focal subject, 3 tones plus black, like a vintage stamp. Keep content inside a 62 × 62 centre with 4 units of air; smallest detail 2.5 units; at most 25 shapes; no more than half of the area lit. The subject is: **[SUBJECT FROM THE TABLE]**. Match this example's drawing style and format exactly: **[paste the example above]**. Return only the SVG.

Ask for 3 options per stamp and keep the clearest one at small size: view each at **61 × 61 px** before choosing.

## 7. What happens after Gemini gives you the SVGs

Send me the files named `s-<id>.svg`. I turn them into lens symbols, check them in real Chromium 74 at actual size on black, in both the normal and alert variants, and fix anything that is too fine or too bright.
