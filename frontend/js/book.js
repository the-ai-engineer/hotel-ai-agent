import { ensureGuestSession, forgetGuestSession } from './guest-session.js';
const form = document.querySelector('#bookingForm');
const villa = document.querySelector('#bookingVilla');
const checkIn = document.querySelector('#bookingIn');
const checkOut = document.querySelector('#bookingOut');
const guests = document.querySelector('#bookingGuests');
const status = document.querySelector('#bookingStatus');
const review = document.querySelector('#bookingReview');
const confirm = document.querySelector('#confirmBooking');
const params = new URLSearchParams(location.search);
let proposed;
let confirming = false;
if (['forest-suite', 'garden-villa'].includes(params.get('villa'))) villa.value = params.get('villa');
checkIn.value = params.get('check_in') || '';
checkOut.value = params.get('check_out') || '';
guests.value = params.get('guests') || '2';
const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Makassar', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
checkIn.min = today;
checkOut.min = today;
function photo() {
  const image = document.querySelector('#bookingImage');
  image.src = villa.value === 'garden-villa' ? 'assets/bedroom-daylight.png' : 'assets/suite.png';
  image.alt = villa.selectedOptions[0].textContent;
}
photo();
form.addEventListener('input', () => { proposed = undefined; review.hidden = true; status.textContent = ''; photo(); });
function summary(details) {
  const date = value => new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`));
  const nights = (new Date(details.check_out) - new Date(details.check_in)) / 86400000;
  return `${details.villa_name} · ${date(details.check_in)} to ${date(details.check_out)} · ${nights} ${nights === 1 ? 'night' : 'nights'} · ${details.guests} ${details.guests === 1 ? 'guest' : 'guests'}`;
}
async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401) forgetGuestSession();
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Please check your details and try again.');
  }
  return data;
}
form.addEventListener('submit', async event => {
  event.preventDefault();
  if (confirming) return;
  review.hidden = true;
  proposed = undefined;
  const details = { villa_id: villa.value, check_in: checkIn.value, check_out: checkOut.value, guests: Number(guests.value) };
  const current = JSON.stringify(details);
  document.querySelector('#reviewBooking').disabled = true;
  status.textContent = 'Checking availability…';
  try {
    const result = await api(`/api/availability?${new URLSearchParams({ check_in: details.check_in, check_out: details.check_out, guests: details.guests })}`);
    if (current !== JSON.stringify({ villa_id: villa.value, check_in: checkIn.value, check_out: checkOut.value, guests: Number(guests.value) })) return;
    if (result.error) throw new Error(result.message);
    if (!result.cards.some(card => card.id === details.villa_id)) throw new Error(result.status === 'unknown_inventory' ? 'Availability is not recorded for these dates. Choose another stay.' : 'This villa is not available for the whole stay. Try another villa or dates.');
    proposed = { ...details, request_id: crypto.randomUUID() };
    document.querySelector('#bookingSummary').textContent = summary({ ...details, villa_name: villa.selectedOptions[0].textContent });
    status.textContent = '';
    review.hidden = false;
    confirm.focus();
  } catch (error) { status.textContent = error.message; }
  finally { document.querySelector('#reviewBooking').disabled = false; }
});
confirm.addEventListener('click', async () => {
  if (!proposed || confirming) return;
  confirming = true;
  confirm.disabled = true;
  for (const field of form.elements) field.disabled = true;
  status.textContent = 'Confirming your reservation…';
  try {
    await ensureGuestSession();
    const { booking } = await api('/api/bookings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(proposed) });
    showConfirmation(booking);
  } catch (error) { status.textContent = error.message; }
  finally {
    confirming = false;
    confirm.disabled = false;
    for (const field of form.elements) field.disabled = false;
  }
});

function showConfirmation(booking) {
  villa.value = booking.villa_id;
  photo();
  form.hidden = true;
  review.hidden = true;
  status.textContent = '';
  document.querySelector('.booking-details h1').textContent = 'Your reservation';
  document.querySelector('.booking-lead').textContent = 'Your stay details and booking reference.';
  document.querySelector('#bookingConfirmed').hidden = false;
  document.querySelector('#confirmedSummary').textContent = summary(booking);
  document.querySelector('#bookingReference').textContent = booking.reference;
  document.querySelector('#askBooking').dataset.ask = `Can you look up my booking ${booking.reference}?`;
  history.replaceState(null, '', `/book?${new URLSearchParams({ reference: booking.reference })}`);
}
if (params.get('reference')) {
  form.hidden = true;
  status.textContent = 'Loading your reservation…';
  try {
    await ensureGuestSession();
    const { booking } = await api(`/api/bookings/${encodeURIComponent(params.get('reference'))}`);
    showConfirmation(booking);
  } catch (error) {
    status.textContent = error.message;
  }
}
