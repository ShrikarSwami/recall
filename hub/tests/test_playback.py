"""Speech controls must preserve content, suppress side effects, and respect full questions."""
import pytest
from tests.test_brain import brain, ask  # noqa: F401
REPEAT = '''again|repeat|repeat that|say that again|say it again|say that|say it|what|what?|huh|huh?|eh|pardon|pardon me|sorry|sorry what|come again|one more time|once more|again please|could you repeat that|can you repeat yourself|would you say that again|please say it again|say the last thing again|repeat your answer|repeat the last answer|repeat your last response|read that again|read it back|play that again|play it again|replay that|replay the answer|what did you say|what was that|what was that again|what did you just say|what were you saying|what did I miss|I didn't hear you|I didn't catch that|I couldn't hear that|I couldn't hear you|I missed that|I missed your answer|I missed what you said|I did not hear that|I did not catch that|did you say something|can you say that once more|could you go over that again|run that by me again|run that past me again|tell me that again|tell me again|remind me what you said|could I hear that again|let me hear that again|can I hear your answer again|repeat the name|say the name again|what was the name again|what was his name again|what was her name again|say the last part again|I missed the last bit|would you mind repeating that|do you mind saying that again|could you repeat the answer please|please could you say that again thanks|sorry can you repeat that|say again|excuse me|I beg your pardon|can you repeat what you just said'''.split('|')
SLOW = '''slower|slow down|speak slower|talk slower|say it slower|say that slower|say that again slowly|repeat that slowly|repeat that more slowly|a little slower|a bit slower|more slowly|not so fast|you're speaking too fast|you are talking too fast|too fast|take your time saying that|could you slow down|can you speak more slowly|please talk a little slower|say it again but slower|repeat your answer slowly|read that more slowly|read it slower|go a little slower|can you slow your voice down|slow your speech down|speak at a slower pace|use a slower voice|less quickly please|could you say that a little more slowly|could you repeat that but slower|I need you to speak slower|that was too fast|say the answer slowly|would you mind speaking more slowly|please slow down a bit|slow it down|a tad slower|repeat that at a slower pace|speak a bit more slowly'''.split('|')
STOP = '''stop|stop talking|stop speaking|stop now|stop please|please stop|stop the audio|stop the voice|stop reading|stop that|stop it|cancel|cancel that|cancel the answer|cancel the reply|cancel the response|be quiet|quiet|quiet please|silence|hush|shush|shut up|enough|that's enough|that is enough|enough now|no more|no more talking|I have heard enough|I've heard enough|I heard enough|you can stop|you can stop talking|you can be quiet now|you can stop now|please stop talking now|could you stop speaking please|can you stop the audio|would you stop reading that|never mind|nevermind|forget it|leave it|leave it there|leave it at that|drop it|cancel what I asked|I changed my mind|I don't want to hear more|I do not want to hear more|I need some silence|I need quiet|I need you to stop|pause|pause that|pause the audio|hold on|hold on a second|hang on|wait a second|give me a moment|stop for a moment|stop for now|stop the explanation|stop answering|can you be quiet|could you hush|please give me some quiet|no more audio|mute|mute yourself|mute the voice|mute the audio|turn off the voice|do not continue|don't continue|don't say any more|do not say any more|that will do|that'll do|okay enough|alright stop|thanks that is enough|that's all|all done|we are done|I'm done|cut it out|cut it|stop the playback|turn it off|turn that off|quiet down|stop saying that'''.split('|')
NEGATIVE = '''what time is it|what is this event|what does he do|what did we do together today|what should I say|what is a bus stop|where is the bus stop|stop at the grocery store|do not stop talking|don't stop|please keep talking|never stop learning|slow cook some rice|how slow is the network|say that word in Spanish|repeat purchases are expensive|repeat after me tomorrow|no thanks|yes|uh huh|how do I cancel a subscription|can you stop by the shop|I need to stop at home'''.split('|')
@pytest.mark.parametrize('phrase',REPEAT)
def test_repeat(brain,phrase):
 original=brain._reply('The workshop starts at ten.','Workshop','kb:faq')
 r=ask(brain,phrase)
 assert r.intent=='speech_repeat' and r.speech==original.speech and r.lines==original.lines
 assert r.alert is None
@pytest.mark.parametrize('phrase',SLOW)
def test_slow(brain,phrase):
 original=brain._reply('The workshop starts at ten.','Workshop','kb:faq')
 r=ask(brain,phrase)
 assert r.intent=='speech_slow' and r.speech==original.speech and 0<r.speech_rate<1
@pytest.mark.parametrize('phrase',STOP)
def test_stop(brain,phrase):
 brain.saw('dev');ask(brain,'who is this')
 r=ask(brain,phrase)
 assert r.intent=='speech_stop' and not r.speech and not r.lines
 assert brain.offer is None and r.alert is None
@pytest.mark.parametrize('phrase',NEGATIVE)
def test_negative(brain,phrase):
 brain._reply('A previous answer.','Answer','kb:faq')
 assert not ask(brain,phrase).intent.startswith('speech_')
def test_no_previous(brain):
 r=ask(brain,'huh?')
 assert r.intent=='speech_repeat_empty' and not r.alert and brain.offer is None
def test_no_repeated_alert(brain):
 first=ask(brain,"I'm scared");assert first.alert
 r=ask(brain,'again');assert r.speech==first.speech and r.alert is None
def test_pending_offer_is_repeated_without_advancing(brain):
 brain.saw('dev');first=ask(brain,'who is this')
 r=ask(brain,'huh?');assert r.speech==first.speech and r.offer=='more'
 assert ask(brain,'yes').intent=='offer_yes'
def test_renamed_wake(brain):
 brain.cfg['wakeWord']='Mika';brain._reply('A previous answer.','Answer','kb:faq')
 assert ask(brain,'Mika, say that again please').intent=='speech_repeat'
 assert ask(brain,'Mika, stop talking').intent=='speech_stop'

def test_polite_wrappers_cover_over_a_thousand_forms():
 from lucia.playback import command
 prefixes=['','please ','can you ','could you ','would you ','will you ','hey can you ',
           'sorry could you ','please can you ','could you please ','can you please ',
           'would you please ','could you just ','please would you ']
 suffixes=['',' please',' thanks',' thank you',' for me',' now']
 cases={'repeat':['repeat that','say it again','read that again','play it again'],
        'slow':['speak slower','talk slower','slow down','say that slowly'],
        'stop':['stop talking','be quiet','stop reading','cancel that']}
 for want,forms in cases.items():
  for form in forms:
   for before in prefixes:
    for after in suffixes:assert command(before+form+after)==want,(before+form+after,want)
