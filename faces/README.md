# faces/ (local only, never committed)

Everything in this folder except this README is gitignored. Photos never leave the Mac.

```
faces/shrikar/front.jpg   faces/shrikar/left.jpg   faces/shrikar/right.jpg
faces/abhiram/...         faces/isha/...           faces/sid/...
```

The folder name must match the `id:` in `knowledge/people/<id>.md`. Any filenames work; `.jpg`/`.png` only
(on an iPhone, export or AirDrop as "Most Compatible" so you don't get HEIC).

## Taking the photos

- **Front:** straight on, eyes level, face filling about a third of the frame. This one matters most.
- **Left / right:** turned **about 30–45°**, not a full 90° side profile. With a true profile the detector can't
  see both eyes and the photo gets skipped. The glasses mostly see people from the front anyway.
- Take them **at the venue, in venue lighting**, without sunglasses or hats. Bonus: one taken from the glasses'
  own camera (`hub/probe_out/` frames) matches demo conditions best.

## Check and load

```bash
cd hub && uv run python -m lucia.faces        # per-photo "face found?" + how well people are told apart
curl -XPOST localhost:9100/api/reload         # load new photos into the running hub (no restart)
```

Look for `<-- would NOT match` lines. If someone's left/right photo fails, retake it at a smaller angle.
Embeddings are kept in memory only; delete the photos after the event.
