const id = window.location.pathname.split('/')[2];
const detail = document.querySelector('#villaDetail');
const text = (selector, value) => { document.querySelector(selector).textContent = value; };

try {
  const response = await fetch(`/api/villas/${encodeURIComponent(id)}`);
  if (!response.ok) throw new Error('Villa information is unavailable. Please try again or ask the concierge.');
  const villa = await response.json();
  document.title = `${villa.name} · Sanctuary Hotel`;
  text('#detailTitle', villa.name);
  text('#detailDescription', villa.description);
  text('#detailBeds', villa.beds.join(' · '));
  text('#detailCapacity', `Up to ${villa.capacity}`);
  text('#detailBedrooms', villa.bedrooms);
  for (const amenity of villa.amenities) {
    const item = document.createElement('li');
    item.textContent = amenity;
    document.querySelector('#detailAmenities').append(item);
  }
  text('#detailPool', villa.private_pool && !villa.pool_fenced
    ? 'The private pool is unfenced. Children need adult supervision.' : '');
  const image = document.querySelector('#detailImage');
  // Published villa data is validated at import; keep asset URLs local here too.
  if (/^assets\/[a-z0-9-]+\.png$/.test(villa.image)) {
    image.src = villa.image;
    image.alt = villa.name;
    document.querySelector('#villaHero').hidden = false;
  }
  document.querySelector('#detailEnquire').dataset.ask = `Can you check availability for the ${villa.name}?`;
  document.querySelector('#detailFacts').hidden = false;
  const other = villa.id === 'forest-suite'
    ? { id: 'garden-villa', name: 'Garden Villa' }
    : { id: 'forest-suite', name: 'Forest Suite' };
  const link = document.querySelector('#otherVillaLink');
  link.href = `/villas/${other.id}`;
  link.textContent = other.name;
  document.querySelector('#otherVilla').hidden = false;
} catch (error) {
  text('#detailDescription', error.message);
} finally {
  detail.setAttribute('aria-busy', 'false');
}
