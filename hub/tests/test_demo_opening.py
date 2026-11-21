"""The judge can ask for examples without a model or a caregiver alert."""
import asyncio
from pathlib import Path

import pytest

from lucia.brain import Brain
from lucia.config import KNOWLEDGE_DIR, load_config
from lucia.knowledge import load


@pytest.mark.parametrize("question", [
    "what can I ask you", "what can I ask", "what questions can I ask you",
    "give me some examples", "what can you help me with", "how can you help me",
    "what can you help me", "what can you do",
])
def test_opening_gives_concrete_questions(question):
    cfg = load_config(Path("../config/app.example.json"))
    cfg["appName"] = cfg["wakeWord"] = "Demo Assistant"
    b = Brain(cfg, load(KNOWLEDGE_DIR))
    reply = asyncio.run(b.answer(question))
    assert reply.intent == "kb:faq" and reply.alert is None
    assert '"Who is this?"' in reply.speech and '"Where am I?"' in reply.speech
    assert "Demo Assistant" in reply.speech and "Go-go" not in reply.speech


@pytest.mark.parametrize("question", [
    "help me", "please help me", "help me now", "can you help me",
    "help me with this, I'm scared", "I want to go home", "Go-go, help me",
])
def test_actual_distress_still_alerts(question):
    b = Brain(load_config(Path("../config/app.example.json")), load(KNOWLEDGE_DIR))
    reply = asyncio.run(b.answer(question))
    assert reply.intent == "distress" and reply.alert


def test_opening_answer_is_prewarmed(tmp_path):
    from tests.test_playback_hub import make_hub

    async def run():
        h = make_hub(tmp_path)
        await h.warm_voice()
        reply = await h.brain.answer("what can I ask you")
        assert reply.speech in [text for text, _ in h.voice.calls]
        await h.llm.client.aclose()
    asyncio.run(run())
