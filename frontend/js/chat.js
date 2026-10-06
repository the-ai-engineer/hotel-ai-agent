// Recording baseline: the widget opens, but no agent is connected yet.
const chat = document.querySelector('#chat');
const launch = document.querySelector('#launch');
const close = document.querySelector('#closeChat');
const question = document.querySelector('#question');
let opener;

function openChat(button) {
  opener = button;
  chat.hidden = false;
  launch.hidden = true;
  close.focus();
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
document.querySelector('#chatForm').addEventListener('submit', (event) => {
  event.preventDefault();
});
