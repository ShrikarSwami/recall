"""Real Hub output scheduling with only hardware, transcription and TTS replaced."""
import asyncio
import json
import time
from pathlib import Path

from lucia.server import Hub
from lucia.config import load_config

class Socket:
 def __init__(self): self.messages=[]; self.audio=[]
 async def send_text(self,s): self.messages.append(json.loads(s))
 async def send_bytes(self,b): self.audio.append(b)
class Voice:
 OUT_RATE=22050
 def __init__(self):self.calls=[];self.entered=None;self.release=None
 async def pcm(self,text,rate=1.0):
  self.calls.append((text,rate))
  if self.entered:self.entered.set();await self.release.wait()
  return b'\0'*8820
class STT:
 last_ms=0
 def __init__(self,text):self.text=text
 async def transcribe(self,pcm):return self.text

def make_hub(tmp_path):
 h=Hub();h.cfg=load_config(Path('../config/app.example.json'));h.brain.cfg=h.cfg
 h.log_path=tmp_path/'events.jsonl';h.voice=Voice();h.glasses=Socket()
 return h

def test_stop_discards_audio_still_rendering(tmp_path):
 async def run():
  h=make_hub(tmp_path);h.voice.entered=asyncio.Event();h.voice.release=asyncio.Event()
  t=asyncio.create_task(h.say(h.brain._reply('A long answer.','Answer','kb:faq')))
  await h.voice.entered.wait()
  await asyncio.wait_for(h.question('stop talking'),1)
  assert any(m['type']=='audio_stop' for m in h.glasses.messages)
  assert any(m['type']=='clear' for m in h.glasses.messages)
  h.voice.release.set();await t
  assert not h.glasses.audio and h.brain.offer is None
  await h.llm.client.aclose()
 asyncio.run(run())

def test_slow_rate_reaches_audio_renderer(tmp_path):
 async def run():
  h=make_hub(tmp_path);h.brain._reply('A saved answer.','Answer','kb:faq')
  await h.question('say that again slowly')
  assert h.voice.calls==[('A saved answer.',0.72)]
  assert h.glasses.audio
  await h.llm.client.aclose()
 asyncio.run(run())

def test_one_word_with_wake_is_a_command(tmp_path):
 async def run():
  h=make_hub(tmp_path);h.stt=STT(h.cfg['wakeWord']+', stop')
  await h.utterance(b'')
  assert any(m['type']=='audio_stop' for m in h.glasses.messages)
  await h.llm.client.aclose()
 asyncio.run(run())

def test_bare_huh_only_works_in_short_followup_window(tmp_path):
 async def run():
  h=make_hub(tmp_path);h.stt=STT('huh?');h.brain._reply('A saved answer.','Answer','kb:faq')
  await h.utterance(b'');assert not h.voice.calls
  h.followup_until=time.time()+10
  await h.utterance(b'')
  assert h.voice.calls==[('A saved answer.',1.0)]
  await h.llm.client.aclose()
 asyncio.run(run())

def test_playback_echo_cannot_start_a_new_question(tmp_path):
 async def run():
  h=make_hub(tmp_path);h.stt=STT(h.cfg['wakeWord']+', who is this?')
  await h.utterance(b'',during_playback=True)
  assert not h.voice.calls
  h.stt=STT(h.cfg['wakeWord']+', stop talking')
  await h.utterance(b'',during_playback=True)
  assert any(m['type']=='audio_stop' for m in h.glasses.messages)
  await h.llm.client.aclose()
 asyncio.run(run())

def test_stop_during_stream_prevents_remaining_chunks(tmp_path):
 async def run():
  h=make_hub(tmp_path)
  class LongVoice(Voice):
   async def pcm(self,text,rate=1):return b'\0'*88200
  h.voice=LongVoice()
  t=asyncio.create_task(h.say(h.brain._reply('A long answer.','Answer','kb:faq')))
  while not h.glasses.audio:await asyncio.sleep(0)
  await h.question('enough please')
  sent=len(h.glasses.audio)
  await t
  assert len(h.glasses.audio)==sent and sent<10
  await h.llm.client.aclose()
 asyncio.run(run())

def test_quick_followup_after_audio_tail_is_not_discarded(tmp_path):
 async def run():
  h=make_hub(tmp_path);h.stt=STT('huh?');h.brain._reply('A saved answer.','Answer','kb:faq')
  h.playing_until=time.time()-0.01;h.followup_until=time.time()+10
  await h.utterance(b'',during_playback=True)
  assert h.voice.calls==[('A saved answer.',1.0)]
  await h.llm.client.aclose()
 asyncio.run(run())

def test_stop_cancels_a_pending_model_answer(tmp_path):
 async def run():
  h=make_hub(tmp_path);entered=asyncio.Event()
  class WaitingModel:
   async def choose(self,*args):entered.set();await asyncio.Event().wait()
   async def freeform(self,*args):entered.set();await asyncio.Event().wait()
  h.brain.llm=WaitingModel()
  question=asyncio.create_task(h.question('what is the airspeed velocity of a swallow'))
  await asyncio.wait_for(entered.wait(),2)
  await h.question('stop')
  await asyncio.wait_for(question,1)
  assert not h.glasses.audio and not h.answer_tasks and h.brain.offer is None
  await h.llm.client.aclose()
 asyncio.run(run())

def test_stop_keeps_fall_detection_imu_streaming(tmp_path):
 async def run():
  h=make_hub(tmp_path);h.cfg['falls']={'enabled':True};h.imu_for_offer=True
  await h.question('stop')
  imu=[m for m in h.glasses.messages if m['type']=='imu']
  assert imu and imu[-1]['on'] is True
  assert h.brain.offer is None and not h.voice.calls
  await h.llm.client.aclose()
 asyncio.run(run())
