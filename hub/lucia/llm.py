"""Ollama client: EnverThor first, local Mac second, with hard timeouts.
The LLM only *chooses* between stored answers or describes the scene; it never states facts."""
from __future__ import annotations

import base64
import re
import time

import httpx


class LLM:
    def __init__(self, cfg: dict):
        m = cfg["models"]
        self.targets = [(m["primary"]["host"], m["primary"]["text"], m["primary"].get("vision"))]
        if m.get("fallback"):
            self.targets.append((m["fallback"]["host"], m["fallback"]["text"], m["fallback"].get("vision")))
        self.timeout = m.get("fallbackAfterMs", 2500) / 1000
        self.client = httpx.AsyncClient()
        self.last_ms: float | None = None

    async def _chat(self, host: str, model: str, prompt: str, image: bytes | None, timeout: float, n: int) -> str:
        msg: dict = {"role": "user", "content": prompt}
        if image is not None:
            msg["images"] = [base64.b64encode(image).decode()]
        r = await self.client.post(f"{host}/api/chat", timeout=timeout, json={
            "model": model, "messages": [msg], "stream": False, "keep_alive": "120m",
            "options": {"num_predict": n, "temperature": 0},
        })
        r.raise_for_status()
        return r.json()["message"]["content"].strip()

    async def ask(self, prompt: str, image: bytes | None = None, n: int = 12, timeout: float | None = None) -> str | None:
        for host, text_model, vision_model in self.targets:
            model = vision_model if image is not None else text_model
            if not model:
                continue
            t0 = time.perf_counter()
            try:
                out = await self._chat(host, model, prompt, image, timeout or self.timeout, n)
                self.last_ms = (time.perf_counter() - t0) * 1000
                return out
            except Exception as e:
                print(f"[llm] {host} {model} failed after {(time.perf_counter()-t0)*1000:.0f} ms: {e!r}")
        return None

    async def choose(self, question: str, options: list[str]) -> int | None:
        """Returns the 0-based index of the option that asks the same thing, or None."""
        listing = "\n".join(f"{i + 1}. {o}" for i, o in enumerate(options))
        out = await self.ask(
            "A person with memory loss asked a question out loud (speech-to-text, may have errors).\n"
            f'They asked: "{question}"\n\nWhich of these stored questions means the same thing?\n{listing}\n\n'
            "Reply with only the number, or 0 if none of them match.", n=4)
        if out is None:
            return None
        m = re.search(r"\d+", out)
        k = int(m.group()) if m else 0
        return k - 1 if 1 <= k <= len(options) else -1

    async def describe(self, jpeg: bytes) -> str | None:
        return await self.ask(
            "You help a person with memory loss. In one short, calm sentence (max 15 words), say where they "
            "are or what is in front of them. Don't mention the camera. Don't identify anyone by name.",
            image=jpeg, n=40, timeout=8)

    async def freeform(self, question: str, patient: str, recent: list[str] | None = None) -> str | None:
        """Off-script questions (a judge asks something we never wrote down). Short, kind, no invented
        personal facts, no medical advice."""
        context = ("\nEarlier in this conversation:\n" + "\n".join(recent[-4:])) if recent else ""
        prompt = (
            f"You are Lucia, a gentle voice assistant inside smart glasses worn by {patient}, who has memory loss. "
            "Answer in at most 2 short sentences (under 30 words), warm and calm, plain words, no lists or markdown. "
            "Never give medical advice; for health questions say a doctor or their caregiver can help. "
            f"Never make up facts about {patient}, their family, friends, plans or past; if asked something "
            "personal you don't know, say you're not sure." + context +
            f"\n\nThey asked: \"{question}\"\nLucia says:")
        out = await self.ask(prompt, n=70, timeout=6)
        if not out:
            return None
        return out.strip().strip('"').split("\n")[0][:240]

    async def warm(self) -> None:
        await self.ask("Say OK.", n=2, timeout=30)
