// Run: node sim/test-playback.cjs. Exercises the real offline answer logic without browser UI.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ctx = {window: {MOCK_KB: JSON.parse(fs.readFileSync(__dirname + '/mock-kb.json', 'utf8'))}, Date};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(__dirname + '/mock-brain.js','utf8'),ctx);
const b=ctx.window.MockBrain;
const first=b.answer('who are you?');
assert.equal(b.answer('huh?').intent,'speech_repeat');
assert.equal(b.answer('say that again').speech,first.speech);
assert.equal(b.answer('please speak slower').speech,first.speech);
assert.ok(b.answer('please speak slower').speech_rate<1);
const stop=b.answer('stop talking');
assert.equal(stop.intent,'speech_stop');assert.equal(stop.type,'clear');assert.equal(stop.speech,'');
assert.notEqual(b.answer('what time is it?').intent,'speech_repeat');
console.log('Mock replay, slower speech, stop, and ordinary question checks passed.');

const corpus=JSON.parse(fs.readFileSync(__dirname+'/../hub/tests/fixtures/playback_phrases.json','utf8'));
for (const kind of ['repeat','slow','stop']) for (const phrase of corpus[kind]) assert.equal(b.control(phrase),kind,phrase);
for (const phrase of corpus.negative) assert.equal(b.control(phrase),null,phrase);
console.log('Shared grammar passes the full authored corpus in JavaScript.');
