import { ensureGuestSession, forgetGuestSession } from './guest-session.js';
import { renderReply, streamReply } from './reply.js';

const chat = document.querySelector('#chat');
const launch = document.querySelector('#launch');
const close = document.querySelector('#closeChat');
const question = document.querySelector('#question');
const form = document.querySelector('#chatForm');
const send = form.querySelector('[type=submit]');
const messages = document.querySelector('#messages');
const content = document.querySelector('#chatContent');
const stop = document.querySelector('#stopAnswer');
const welcome = document.querySelector('#chatWelcome');
const reset = document.querySelector('#newConversation');
const resetConfirm = document.querySelector('#resetConfirm');
const cancelReset = document.querySelector('#cancelReset');
const confirmReset = document.querySelector('#confirmReset');
let opener;
let ready = false;
let preparing;
let controller;

function bubble(text, role) {
  const node = document.createElement('div');
  node.className = `concierge-message ${role}`;
  const body = document.createElement('div');
  body.className = 'concierge-text';
  if (role === 'assistant') renderReply(body, text);
  else body.textContent = text;
  node.append(body);
  messages.append(node);
  welcome.hidden = true;
  content.scrollTop = content.scrollHeight;
  return node;
}

function renderSources(node, sources) {
  const group = document.createElement('div');
  group.className = 'concierge-sources';
  for (const source of sources) {
    if (!/^\/api\/sources\/[a-z0-9-]+\/[1-9][0-9]*$/.test(source.url)) continue;
    const link = document.createElement('a');
    link.href = source.url;
    link.target = '_blank';
    link.rel = 'noopener';
    link.textContent = `${source.title} · v${source.revision}`;
    link.className = 'concierge-source';
    group.append(link);
  }
  if (group.childElementCount) node.append(group);
}

function renderAvailability(node, result) {
  if (!result) return;
  const date = (value) => new Intl.DateTimeFormat('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC',
  }).format(new Date(`${value}T00:00:00Z`));
  const summary = document.createElement('div');
  summary.className = 'availability-summary';
  summary.textContent = `${date(result.check_in)} – ${date(result.check_out)} · ${result.nights} ${result.nights === 1 ? 'night' : 'nights'} · ${result.guests} ${result.guests === 1 ? 'guest' : 'guests'}`;
  node.append(summary);
  if (result.status === 'unknown_inventory' || result.status === 'no_match') {
    const outcome = document.createElement('p');
    outcome.className = 'villa-card-details';
    outcome.textContent = result.status === 'unknown_inventory'
      ? 'Availability is not recorded for these dates.'
      : 'No villa matches the complete stay and party size.';
    node.append(outcome);
  }
  const cards = document.createElement('div');
  cards.className = 'villa-results';
  const approvedImages = {
    'forest-suite': 'assets/suite.png',
    'garden-villa': 'assets/bedroom-daylight.png',
  };
  for (const villa of result.cards || []) {
    if (!approvedImages[villa.id] || villa.image !== approvedImages[villa.id]) continue;
    const card = document.createElement('article');
    card.className = 'villa-card';
    const image = document.createElement('img');
    image.className = 'villa-card-photo';
    image.src = villa.image;
    image.alt = villa.name;
    image.loading = 'lazy';
    const body = document.createElement('div');
    body.className = 'villa-card-body';
    const title = document.createElement('h3');
    title.className = 'villa-card-title';
    title.textContent = villa.name;
    const meta = document.createElement('p');
    meta.className = 'villa-card-meta';
    meta.textContent = `Up to ${villa.capacity} guests · ${villa.bedrooms} ${villa.bedrooms === 1 ? 'bedroom' : 'bedrooms'}`;
    const details = document.createElement('p');
    details.className = 'villa-card-details';
    details.textContent = villa.beds.join(' · ');
    const link = document.createElement('a');
    link.className = 'villa-card-link';
    link.href = `/villas/${villa.id}`;
    link.textContent = 'View villa';
    const reserve = document.createElement('a');
    reserve.className = 'villa-card-link villa-reserve';
    reserve.href = `/book?${new URLSearchParams({ villa: villa.id, check_in: result.check_in, check_out: result.check_out, guests: result.guests })}`;
    reserve.textContent = 'Reserve this villa';
    body.append(title, meta, details, link, reserve);
    card.append(image, body);
    cards.append(card);
  }
  if (cards.childElementCount) node.append(cards);
  const note = document.createElement('p');
  note.className = 'villa-card-details';
  const checked = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(result.checked_at));
  note.textContent = `Fictional inventory · checked ${checked} · no reservation held`;
  node.append(note);
}

function renderHotelRequest(node, request) {
  if (!request) return;
  const panel = document.createElement('section');
  panel.className = 'hotel-request';
  const heading = document.createElement('h3');
  heading.textContent = `Note for booking ${request.reference}`;
  const note = document.createElement('p');
  note.textContent = request.note;
  const status = document.createElement('p');
  status.className = 'request-status';
  const button = document.createElement('button');
  button.type = 'button';
  button.textContent = 'Send request';
  const update = () => {
    button.hidden = request.status !== 'draft';
    status.textContent = request.status === 'pending_review'
      ? 'Saved for hotel review. Your booking is unchanged.'
      : request.status === 'superseded' ? 'Replaced by a newer request.'
      : 'Review this note before sending. The draft expires in 10 minutes.';
  };
  button.addEventListener('click', async () => {
    button.disabled = true;
    try {
      const response = await api(`/api/requests/${request.id}/confirm`, { method: 'POST' });
      request = await response.json();
      update();
    } catch (error) {
      status.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
  panel.append(heading, note, status, button);
  update();
  node.append(panel);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    if (response.status === 401) { ready = false; forgetGuestSession(); }
    const data = await response.json().catch(() => ({}));
    throw new Error(typeof data.detail === 'string' ? data.detail : 'The concierge is unavailable. Please try again.');
  }
  return response;
}

function prepare() {
  if (ready) return Promise.resolve();
  if (!preparing) {
    preparing = (async () => {
      await ensureGuestSession();
      const response = await api('/api/history');
      const data = await response.json();
      messages.replaceChildren();
      welcome.hidden = data.turns.length > 0;
      for (const turn of data.turns) {
        bubble(turn.question, 'guest');
        const node = bubble(turn.answer, 'assistant');
        renderSources(node, turn.sources);
        renderAvailability(node, turn.availability);
        renderHotelRequest(node, turn.hotel_request);
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
  if (button.dataset?.ask) question.focus();
  else close.focus();
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
  if (event.key === 'Escape') {
    if (!resetConfirm.hidden) { resetConfirm.hidden = true; reset.focus(); }
    else closeChat();
  }
});
stop.addEventListener('click', () => controller?.abort());
reset.addEventListener('click', () => {
  resetConfirm.hidden = false;
  cancelReset.focus();
});
cancelReset.addEventListener('click', () => {
  resetConfirm.hidden = true;
  reset.focus();
});
confirmReset.addEventListener('click', async () => {
  confirmReset.disabled = true;
  cancelReset.disabled = true;
  send.disabled = true;
  question.disabled = true;
  reset.disabled = true;
  try {
    await prepare();
    await api('/api/conversation', { method: 'POST' });
    messages.replaceChildren();
    welcome.hidden = false;
    resetConfirm.hidden = true;
    question.value = '';
    question.focus();
  } catch (error) {
    bubble(error.message, 'notice');
  } finally {
    confirmReset.disabled = false;
    cancelReset.disabled = false;
    send.disabled = false;
    question.disabled = false;
    reset.disabled = false;
    question.focus();
  }
});

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
  if (!resetConfirm.hidden) return;
  controller = new AbortController();
  reset.disabled = true;
  messages.setAttribute('aria-busy', 'true');
  send.disabled = true;
  question.disabled = true;
  stop.hidden = false;
  let node;
  let committed = false;
  let rendering;
  try {
    await prepare();
    bubble(text, 'guest');
    question.value = '';
    node = bubble('Checking hotel information…', 'assistant');
    rendering = streamReply(node.querySelector('.concierge-text'), () => {
      content.scrollTop = content.scrollHeight;
    });
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
        rendering.update(draft);
      } else if (name === 'result') {
        rendering.finish(data.answer);
        renderSources(node, data.sources);
        renderAvailability(node, data.availability);
        renderHotelRequest(node, data.hotel_request);
        committed = true;
        content.scrollTop = content.scrollHeight;
      } else if (name === 'error') {
        throw new Error(data.message);
      }
    });
    if (!committed) throw new Error('The connection ended before the answer was saved. Please try again.');
  } catch (error) {
    if (!committed) {
      if (node) node.remove();
      bubble(error.name === 'AbortError' ? 'Answer stopped. You can ask again.' : error.message, 'notice');
      question.value = text;
    }
  } finally {
    rendering?.cancel();
    controller = undefined;
    reset.disabled = false;
    messages.setAttribute('aria-busy', 'false');
    send.disabled = false;
    question.disabled = false;
    stop.hidden = true;
    question.focus();
  }
});
