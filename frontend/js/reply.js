import { marked } from './vendor/marked.js';
import DOMPurify from './vendor/dompurify.js';

export function renderReply(node, text) {
  const html = DOMPurify.sanitize(marked.parse(text, { breaks: true }), {
    ALLOWED_TAGS: ['p', 'strong', 'em', 'ul', 'ol', 'li', 'br', 'code', 'pre', 'blockquote'],
    ALLOWED_ATTR: [],
  });
  if (node.innerHTML !== html) node.innerHTML = html;
}

// Batch token bursts; always flush the final saved answer immediately.
export function streamReply(node, onRender) {
  let latest = '';
  let timer;
  function flush() {
    timer = undefined;
    renderReply(node, latest);
    onRender();
  }
  function cancel() {
    clearTimeout(timer);
    timer = undefined;
  }
  return {
    update(text) {
      latest = text;
      if (!timer) timer = setTimeout(flush, 100);
    },
    finish(text) {
      cancel();
      latest = text;
      flush();
    },
    cancel,
  };
}
