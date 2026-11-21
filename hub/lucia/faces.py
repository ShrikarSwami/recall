"""Face recognition with ShrikarSwami/face_id (vendored in vendor/face_id, gitignored).

Enroll: faces/<person_id>/*.jpg → one prototype embedding per person (kept in memory only).
Identify: the largest face in the frame (the person you're facing), cosine vs prototypes.
"""
from __future__ import annotations

import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np

from .config import ROOT

sys.path.insert(0, str(ROOT / "vendor"))


class Faces:
    def __init__(self, faces_dir: Path, threshold: float = 0.45):
        from face_id.utils.align import align_face
        from face_id.utils.detect import detect_faces
        from face_id.utils.embed import compute_embedding
        self._detect, self._align, self._embed = detect_faces, align_face, compute_embedding
        self.dir = faces_dir
        self.threshold = threshold
        self.protos: dict[str, np.ndarray] = {}
        self.pool = ThreadPoolExecutor(max_workers=1)

    def _embed_largest(self, img: np.ndarray) -> np.ndarray | None:
        dets = self._detect(img)
        if not dets:
            return None
        d = max(dets, key=lambda d: (d["bbox"][2] - d["bbox"][0]) * (d["bbox"][3] - d["bbox"][1]))
        aligned = self._align(img, d["landmarks"])
        e = self._embed(aligned)
        return None if e is None else e / (np.linalg.norm(e) + 1e-9)

    def enroll_all(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for person_dir in sorted(p for p in self.dir.iterdir() if p.is_dir()):
            embs = []
            for f in sorted(person_dir.glob("*")):
                if f.suffix.lower() not in (".jpg", ".jpeg", ".png", ".heic"):
                    continue
                img = cv2.imread(str(f))
                if img is None:
                    continue
                e = self._embed_largest(img)
                if e is not None:
                    embs.append(e)
            if embs:
                p = np.mean(embs, axis=0)
                self.protos[person_dir.name] = p / np.linalg.norm(p)
                counts[person_dir.name] = len(embs)
        return counts

    def _identify(self, jpeg: bytes) -> tuple[bool, str | None, float]:
        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return False, None, 0.0
        e = self._embed_largest(img)
        if e is None:
            return False, None, 0.0
        if not self.protos:
            return True, None, 0.0
        name, score = max(((n, float(p @ e)) for n, p in self.protos.items()), key=lambda x: x[1])
        return True, (name if score >= self.threshold else None), score

    async def identify(self, jpeg: bytes) -> tuple[bool, str | None, float]:
        """(face_found, person_id_or_None, similarity)."""
        return await asyncio.get_running_loop().run_in_executor(self.pool, self._identify, jpeg)
