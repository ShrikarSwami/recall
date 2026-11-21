# faces/ (local only, never committed)

Everything in this folder except this README is gitignored.

```
faces/<person_id>/front.jpg
faces/<person_id>/left.jpg
faces/<person_id>/right.jpg
```

`<person_id>` must match the `id:` in `knowledge/people/<person_id>.md`. The hub enrolls these with
[`face_id`](https://github.com/ShrikarSwami/face_id) and keeps only embeddings. Delete the photos after the event.
