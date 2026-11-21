"""Anchored speech-control grammar. No substring/fuzzy matching for short commands."""
import re

_PREFIX = re.compile(r'^(?:would you mind|do you mind|i need you to|could you|would you|can you|will you|please|sorry|hey|okay|alright|thanks|just)\s+')
_SUFFIX = re.compile(r'\s+(?:thank you|thanks|please|for me|right now|now)$')
_REPEAT = re.compile(
 r"(?:say again|excuse me|i beg your pardon|repeat what you just said|again|repeat(?: (?:that|it|yourself|the name|your answer|the (?:last )?answer|your last response))?|"
 r"say (?:it|that|the name|the last (?:thing|part))(?: (?:again|once more|one more time))?|"
 r"(?:read|play) (?:it|that)(?: (?:again|back))?|replay (?:that|it|the answer)|"
 r"what|huh|eh|pardon(?: me)?|sorry|sorry what|come again|one more time|once more|"
 r"what (?:did you (?:just )?say|was (?:that(?: again)?|(?:his |her |the )?name again)|were you saying|did i miss)|"
 r"i (?:(?:did not|could not) (?:hear|catch) (?:you|that)|missed (?:that|your answer|what you said|the last bit))|"
 r"did you say something|go over (?:it|that) again|run (?:it|that) (?:by|past) me again|"
 r"tell me(?: that)? again|remind me what you said|(?:could i|can i|let me) hear (?:that|it|your answer) again|"
 r"repeating (?:that|it)|saying (?:that|it) again)")
_SLOW = re.compile(
 r"(?:a tad slower|repeat that at a slower pace|slower|(?:a little|a bit) slower|more slowly|less quickly|not so fast|too fast|that was too fast|"
 r"slow (?:down(?: a bit)?|it down|your (?:speech|voice) down)|"
 r"(?:speak|talk)(?: a little| a bit)?(?: more)? (?:slowly|slower)|"
 r"(?:say|read|repeat) (?:it|that|your answer|the answer)(?: again)?(?: but)?(?: a little| a bit)? (?:more slowly|slower|slowly)|"
 r"you are (?:speaking|talking) too fast|take your time saying that|go a little slower|"
 r"speak at a slower pace|use a slower voice|speaking more slowly)")
_STOP = re.compile(
 r"(?:that is all|all done|we are done|i am done|cut it(?: out)?|turn (?:it|that) off|quiet down|stop saying that|stop(?: (?:talking|speaking|reading(?: (?:that|it))?|answering|that|it|the (?:audio|voice|explanation|playback)))?(?: for (?:a moment|now))?|"
 r"cancel(?: (?:that|the (?:answer|reply|response)|what i asked))?|be quiet|quiet|silence|hush|shush|shut up|"
 r"enough|that is enough|no more(?: (?:talking|audio))?|i (?:have )?heard enough|"
 r"you can (?:stop(?: talking)?|be quiet)|never ?mind|forget it|leave it(?: there| at that)?|drop it|"
 r"i changed my mind|i do not want to hear more|i need (?:some silence|quiet)|"
 r"pause(?: (?:that|the audio))?|hold on(?: a second)?|hang on|wait a second|give me a moment|"
 r"give me some quiet|mute(?: (?:yourself|the voice|the audio))?|turn off the voice|"
 r"do not (?:continue|say any more)|that will do)")


def command(text: str, wake: str = '') -> str | None:
    t = text.lower().replace('’', "'")
    for a,b in {"didn't":"did not","couldn't":"could not","you're":"you are","that's":"that is",
                "i've":"i have","don't":"do not","that'll":"that will","i'm":"i am","we're":"we are"}.items():
        t = re.sub(r'\b'+re.escape(a)+r'\b',b,t)
    t = re.sub(r"[^a-z0-9' ]",' ',t)
    t = ' '.join(t.split())
    w = ' '.join(re.sub(r"[^a-z0-9' ]",' ',wake.lower()).split())
    if w:
        t = re.sub(r'^(?:hey )?'+re.escape(w)+r'\b\s*','',t)
    for _ in range(4):
        old=t; t=_PREFIX.sub('',t)
        if not t.endswith(' for now'): t=_SUFFIX.sub('',t)
        if old==t:break
    if _STOP.fullmatch(t):return 'stop'
    if _SLOW.fullmatch(t):return 'slow'
    if _REPEAT.fullmatch(t):return 'repeat'
    return None

# Shared with the offline simulator, which uses the same anchored grammar.
GRAMMAR = {"prefix": _PREFIX.pattern, "suffix": _SUFFIX.pattern, "repeat": _REPEAT.pattern,
           "slow": _SLOW.pattern, "stop": _STOP.pattern}
