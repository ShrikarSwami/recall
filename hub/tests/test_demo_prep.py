"""Demo preparation using the real brain; only speech and messaging are faked."""
import asyncio
import json
from datetime import datetime

from tests.test_playback_hub import make_hub


class Messages:
    def __init__(self):
        self.sent = []

    async def send(self, text, urgent=False):
        self.sent.append((text, urgent))
        return "dry-run"


def test_distress_and_fall_include_context_in_existing_messages(tmp_path):
    async def run():
        h = make_hub(tmp_path)
        h.cfg["voice"]["speakAnswers"] = False
        h.alerts = Messages()
        h.brain.clock = lambda: 1795243200
        h.brain.place = {"name": "City Tech", "at": h.brain.clock()}
        reply = await h.brain.answer("I want to go home")
        await h.say(reply)
        await h.fall()
        assert len(h.alerts.sent) == 2
        distress, fall = h.alerts.sent
        assert distress[0].startswith(h.cfg["appName"] + ":")
        assert "City Tech" in distress[0]
        stamp = datetime.fromtimestamp(h.brain.clock()).astimezone().strftime("%-I:%M %p")
        assert stamp in distress[0]
        assert not distress[1] and fall[1]
        assert "may have fallen" in fall[0] and "City Tech" in fall[0]
        events = [json.loads(line) for line in h.log_path.read_text().splitlines()]
        assert [e["text"] for e in events if e["type"] == "alert"] == [m[0] for m in h.alerts.sent]
        await h.llm.client.aclose()
    asyncio.run(run())


def test_alert_does_not_present_stale_phone_place_as_current(tmp_path):
    h = make_hub(tmp_path)
    h.brain.clock = lambda: 2000
    h.brain.place = {"name": "Old shop", "at": 1}
    assert "Old shop" not in h.alert_text("Test")
    assert h.alert_text("Test").endswith("City Tech, Downtown Brooklyn") or "City Tech" in h.alert_text("Test")
    h.cfg["currentPlace"] = "missing"
    assert h.alert_text("Test").count(" · ") == 1          # time only: no made-up place
    asyncio.run(h.llm.client.aclose())


def test_warmup_renders_exact_intros_without_changing_conversation(tmp_path):
    async def run():
        h = make_hub(tmp_path)
        h.brain._reply("Keep this answer.", "Answer", "kb:faq")
        saved = h.brain.last_answer
        before = list(h.brain.history)
        await h.warm_voice()
        texts = [text for text, rate in h.voice.calls]
        from lucia.brain import Brain
        preview = Brain(h.cfg, h.kb)
        assert preview.greeting().speech in texts
        for pid in h.kb.people:
            assert preview.intro_reply(pid).speech in texts
        assert len(texts) == len(set(texts)) and len(texts) <= 24
        assert list(h.brain.history) == before and h.brain.last_answer is saved
        assert h.brain.offer is None and not h.glasses.audio and not h.glasses.messages
        assert h.voice_warmup["state"] == "ready"
        await h.llm.client.aclose()
    asyncio.run(run())


def test_warmup_refreshes_names_and_reports_empty_audio(tmp_path):
    async def run():
        h = make_hub(tmp_path)
        h.queue_voice_warmup()
        first = h.voice_warm_task
        h.cfg["patient"]["preferredName"] = "Demo Judge"
        h.queue_voice_warmup()
        await h.voice_warm_task
        assert first.cancelled()
        assert any("Hi Demo Judge." in text for text, _ in h.voice.calls)

        class EmptyVoice:
            async def pcm(self, text, rate=1):
                return b""
        h.voice = EmptyVoice()
        await h.warm_voice()
        assert h.voice_warmup["state"] == "partial"
        assert h.voice_warmup["ready"] == 0
        h.cfg["voice"]["speakAnswers"] = False
        await h.warm_voice()
        assert h.voice_warmup["state"] == "disabled"
        await h.llm.client.aclose()
    asyncio.run(run())


def test_alert_context_is_captured_before_speech_finishes(tmp_path):
    async def run():
        h = make_hub(tmp_path)
        h.alerts = Messages()
        h.brain.clock = lambda: 2000
        h.brain.place = {"name": "First place", "at": 2000}

        class MovingVoice:
            async def pcm(self, text, rate=1):
                h.brain.place = {"name": "Next place", "at": 2000}
                return b"\0" * 8820

        h.voice = MovingVoice()
        await h.say(await h.brain.answer("I'm scared"))
        assert "First place" in h.alerts.sent[0][0]
        assert "Next place" not in h.alerts.sent[0][0]
        await h.llm.client.aclose()
    asyncio.run(run())


def test_patient_endpoint_and_reload_refresh_warmup(tmp_path, monkeypatch):
    from lucia import server

    async def run():
        h = make_hub(tmp_path)
        monkeypatch.setattr(server, "hub", h)
        await server.api_patient({"name": "Judge Example"})
        await h.voice_warm_task
        assert any("Hi Judge." in text for text, _ in h.voice.calls)
        h.voice.calls.clear()
        monkeypatch.setattr(server, "load_config", lambda: h.cfg)
        monkeypatch.setattr(h.faces, "enroll_all", lambda: {})
        h.reload()
        await h.voice_warm_task
        assert h.voice.calls and h.voice_warmup["state"] == "ready"
        await h.llm.client.aclose()
    asyncio.run(run())
