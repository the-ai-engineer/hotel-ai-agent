const { readFileSync } = require('node:fs');
const assert = require('node:assert/strict');
const { webcrypto } = require('node:crypto');
const { JSDOM } = require('../node_modules/jsdom');
const { resolve } = require('node:path');
const root = resolve(__dirname, '../..') + '/';
const code = readFileSync(root + 'frontend/js/chat.js', 'utf8').replace(/^import .*;\n/gm, '');
const tick = () => new Promise(resolve => setTimeout(resolve, 10));
const json = (data, status = 200) => ({ ok: status < 400, status, headers: { get: () => 'application/json' }, json: async () => data });
function harness(fetcher) {
  const dom = new JSDOM(readFileSync(root + 'frontend/index.html', 'utf8'), { url: 'http://127.0.0.1:8773', runScripts: 'outside-only' });
  const w = dom.window;
  w.fetch = fetcher;
  w.TextDecoder = TextDecoder;
  w.crypto.randomUUID = webcrypto.randomUUID.bind(webcrypto);
  w.ensureGuestSession = async () => {};
  w.forgetGuestSession = () => {};
  w.renderReply = (node, text) => { node.textContent = text; };
  w.streamReply = node => ({ update(text) { node.textContent = text; }, finish(text) { node.textContent = text; }, cancel() {} });
  w.eval(code);
  return { w, dom, find: id => w.document.getElementById(id), submit(text) {
    w.document.getElementById('question').value = text;
    w.document.getElementById('chatForm').dispatchEvent(new w.Event('submit', { bubbles: true, cancelable: true }));
  }};
}
async function until(predicate) {
  for (let i = 0; i < 200; i++) { if (predicate()) return; await tick(); }
  throw new Error('Widget condition timed out');
}
(async () => {
  const id = '11111111-1111-4111-8111-111111111111';
  let polls = 0;
  let submits = 0;
  const h = harness(async path => {
    if (path === '/api/history') return json({ turns: [], active_turn: { turn_id: id, status_url: `/api/turns/${id}`, question: 'Original question' } });
    if (path.startsWith('/api/turns/')) return json(++polls === 1 ? { status: 'running' } : { status: 'completed', result: { answer: 'Recovered saved reply', sources: [] } });
    if (path === '/api/chat') { submits++; return json({ status: 'completed', result: { answer: 'Next reply', sources: [] } }); }
    throw new Error(path);
  });
  h.w.eval('openChat({})');
  await until(() => h.find('messages').textContent.includes('Recovered saved reply'));
  assert.equal(h.find('question').disabled, false);
  h.submit('Next question');
  await until(() => h.find('messages').textContent.includes('Next reply'));
  assert.equal(submits, 1, 'Recovery must clear the stale controller and permit another turn');
  h.dom.window.close();

  let stopped = false;
  const stop = harness(async (path, options = {}) => {
    if (path === '/api/history') return json({ turns: [] });
    if (path.endsWith('/stop')) { stopped = true; return json({ status: 'interrupted' }); }
    if (path === '/api/chat') return new Promise((resolve, reject) => options.signal.addEventListener('abort', () => reject(new stop.w.DOMException('Stopped', 'AbortError')), { once: true }));
    throw new Error(path);
  });
  stop.submit('Slow question');
  await until(() => !stop.find('stopAnswer').hidden);
  await tick();
  stop.find('stopAnswer').click();
  await until(() => stop.find('messages').textContent.includes('Answer stopped'));
  assert.equal(stopped, true);
  assert.equal(stop.find('question').value, 'Slow question');
  assert.equal(stop.find('question').disabled, false);
  stop.dom.window.close();

  let statusCalls = 0;
  const limit = harness(async path => {
    if (path === '/api/history') return json({ turns: [] });
    if (path === '/api/chat') return json({ detail: 'Request limit reached' }, 429);
    statusCalls++;
    return json({ detail: 'Turn not found' }, 404);
  });
  limit.submit('Limited');
  await until(() => limit.find('messages').textContent.includes('Request limit reached'));
  assert.equal(statusCalls, 0, 'HTTP rejection must retain its useful error, not attempt nonexistent turn recovery');
  limit.dom.window.close();
  console.log('Widget refresh, Stop, retry and overload recovery checks passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
