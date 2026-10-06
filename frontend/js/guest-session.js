// Both booking and chat must share one cookie initialization on a fresh page.
let starting;
export function ensureGuestSession() {
  if (!starting) {
    starting = fetch('/api/session', { method: 'POST' }).then(response => {
      if (!response.ok) throw new Error('Could not start your guest session. Please try again.');
    }).catch(error => { starting = undefined; throw error; });
  }
  return starting;
}
export function forgetGuestSession() { starting = undefined; }
