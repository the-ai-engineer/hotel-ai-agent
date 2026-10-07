const chat = document.querySelector('#chat');
const launch = document.querySelector('#launch');
const close = document.querySelector('#closeChat');
const question = document.querySelector('#question');
const form = document.querySelector('#chatForm');
const send = form.querySelector('[type=submit]');
const messages = document.querySelector('#messages');
const content = document.querySelector('#chatContent');
const stop = document.querySelector('#stopAnswer');
let opener;
let ready = false;
let preparing;
let controller;

function bubble(text, role) {
  const node = document.createElement('div');
  node.className = `concierge-message ${role}`;
  node.textContent = text;
  messages.append(node);
  content.scrollTop = content.scrollHeight;
  return node;
}

function renderSources(node, sources) {
  for (const source of sources) {
    if (!/^\/api\/sources\/[a-z0-9-]+\/[1-9][0-9]*$/.test(source.url)) continue;
    const link = document.createElement('a');
    link.href = source.url;
    link.target = '_blank';
    link.rel = 'noopener';
    link.textContent = `${source.title} · v${source.revision}`;
    link.className = 'concierge-source';
    node.append(link);
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    if (response.status === 401) ready = false;
    const data = await response.json().catch(() => ({}));
    throw new Error(typeof data.detail === 'string' ? data.detail : 'The concierge is unavailable. Please try again.');
  }
  return response;
}

function prepare() {
  if (ready) return Promise.resolve();
  if (!preparing) {
    preparing = (async () => {
      await api('/api/session', { method: 'POST' });
      const response = await api('/api/history');
      const data = await response.json();
      messages.replaceChildren();
      for (const turn of data.turns) {
        bubble(turn.question, 'guest');
        renderSources(bubble(turn.answer, 'assistant'), turn.sources);
      }
      ready = true;
    })().finally(() => { preparing = undefined; });
  }
  return preparing;
}

async function openChat(button) {
  opener = button;
  chat.hidden = false;
  launch.hidden = true;
  close.focus();
  try {
    await prepare();
  } catch (error) {
    bubble(error.message, 'notice');
  }
}

function closeChat() {
  chat.hidden = true;
  launch.hidden = false;
  if (opener?.offsetParent) opener.focus();
  else launch.focus();
}

document.addEventListener('click', (event) => {
  const button = event.target.closest('[data-chat], [data-ask], [data-guide]');
  if (!button) return;
  question.value = button.dataset.ask || '';
  openChat(button);
});
close.addEventListener('click', closeChat);
chat.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') closeChat();
});
stop.addEventListener('click', () => controller?.abort());

// fetch POST streaming works with the same-origin session cookie.
async function readEvents(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let boundary;
      while ((boundary = buffer.indexOf('\n\n')) !== -1) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const name = block.split('\n').find((line) => line.startsWith('event: '))?.slice(7);
        const data = block.split('\n').filter((line) => line.startsWith('data: ')).map((line) => line.slice(6)).join('\n');
        if (name && data) onEvent(name, JSON.parse(data));
      }
      if (done) break;
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const text = question.value.trim();
  if (!text || controller) return;
  controller = new AbortController();
  send.disabled = true;
  question.disabled = true;
  stop.hidden = false;
  let node;
  let committed = false;
  try {
    await prepare();
    bubble(text, 'guest');
    question.value = '';
    node = bubble('Checking hotel information…', 'assistant');
    let draft = '';
    const response = await api('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ turn_id: crypto.randomUUID(), message: text }),
      signal: controller.signal,
    });
    await readEvents(response, (name, data) => {
      if (name === 'text') {
        draft += data.text;
        node.textContent = draft;
      } else if (name === 'result') {
        node.textContent = data.answer;
        renderSources(node, data.sources);
        committed = true;
      } else if (name === 'error') {
        throw new Error(data.message);
      }
      content.scrollTop = content.scrollHeight;
    });
    if (!committed) throw new Error('The connection ended before the answer was saved. Please try again.');
  } catch (error) {
    if (!committed) {
      if (node) node.remove();
      bubble(error.name === 'AbortError' ? 'Answer stopped. You can ask again.' : error.message, 'notice');
      question.value = text;
    }
  } finally {
    controller = undefined;
    send.disabled = false;
    question.disabled = false;
    stop.hidden = true;
    question.focus();
  }
});
