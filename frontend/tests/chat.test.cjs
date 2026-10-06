// Delayed initialization must not rotate cookies or detach a streamed answer.
const { readFileSync } = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { webcrypto } = require('node:crypto');

class Node {
  constructor() { this.children = []; this.handlers = {}; this.value = ''; }
  append(node) { this.children.push(node); node.parent = this; }
  replaceChildren() { this.children = []; }
  focus() {}
  setAttribute() {}
  addEventListener(name, handler) { this.handlers[name] = handler; }
  querySelector(selector) { return selector === '.concierge-text' ? this.children[0] : nodes.send; }
  remove() { this.parent.children = this.parent.children.filter((node) => node !== this); }
}
const names = ['chat', 'launch', 'closeChat', 'question', 'chatForm', 'messages', 'chatContent', 'stopAnswer', 'send', 'chatWelcome', 'newConversation', 'resetConfirm', 'cancelReset', 'confirmReset'];
const nodes = Object.fromEntries(names.map((name) => [name, new Node()]));
nodes.resetConfirm.hidden = true;
const pending = [];
const context = vm.createContext({
  document: {
    querySelector: (selector) => nodes[selector.slice(1)],
    createElement: () => new Node(),
    addEventListener() {},
  },
  fetch: (path) => new Promise((resolve) => pending.push({ path, resolve })),
  AbortController, TextDecoder, crypto: webcrypto,
  ensureGuestSession: () => new Promise(resolve => pending.push({ path: '/api/session', resolve })),
  forgetGuestSession() {},
  renderReply: (node, text) => { node.textContent = text; },
  streamReply: (node) => ({ update(text) { node.textContent = text; }, finish(text) { node.textContent = text; }, cancel() {} }),
});
vm.runInContext(readFileSync('frontend/js/chat.js', 'utf8').replace(/^import .*;\n/gm, ''), context);
const tick = () => new Promise((resolve) => setImmediate(resolve));

(async () => {
  const opened = vm.runInContext('openChat({})', context);
  nodes.question.value = 'Breakfast?';
  const submitted = nodes.chatForm.handlers.submit({ preventDefault() {} });
  await tick();
  assert.deepEqual(pending.map((request) => request.path), ['/api/session']);
  pending[0].resolve({ ok: true });
  await tick();
  assert.deepEqual(pending.map((request) => request.path), ['/api/session', '/api/history']);
  assert.equal(nodes.messages.children.length, 0);
  pending[1].resolve({ ok: true, json: async () => ({ turns: [] }) });
  await tick();
  assert.equal(nodes.messages.children.length, 2);
  let read = 0;
  let cancelled = false;
  let released = false;
  const payload = new TextEncoder().encode('event: result\ndata: {"answer":"Breakfast included","sources":[]}\n\nevent: done\ndata: {}\n\n');
  pending[2].resolve({ ok: true, body: { getReader: () => ({
    read: async () => read++ ? { done: true } : { done: false, value: payload },
    cancel: async () => { cancelled = true; },
    releaseLock() { released = true; },
  }) } });
  await Promise.all([opened, submitted]);
  assert.equal(nodes.messages.children.length, 2);
  assert.equal(nodes.messages.children[1].children[0].textContent, 'Breakfast included');
  assert.equal(cancelled, true);
  assert.equal(released, true);
  console.log('Chat initialization race regression passed.');
})().catch((error) => { console.error(error); process.exitCode = 1; });
