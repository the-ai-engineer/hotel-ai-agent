const $ = s => document.querySelector(s);
const villaData=[{title:'The Forest<br>Suite',meta:'ONE BEDROOM · TWO GUESTS · PRIVATE POOL',image:'assets/suite.png',description:'A one-bedroom villa for two guests, with natural linen, a private pool and forest views.'},{title:'The Garden<br>Villa',meta:'TWO BEDROOMS · FOUR GUESTS · PRIVATE POOL',image:'assets/bedroom-daylight.png',description:'A two-bedroom villa for up to four guests, with a private pool and garden terrace.'},{title:'Terrace<br>Breakfast',meta:'TERRACE SERVICE · REQUEST WITH YOUR HOST',image:'assets/breakfast.png',description:'Fresh fruit, warm pastries, and coffee on your terrace. Ask your host to arrange a breakfast time; availability and any charges require confirmation.'}];let villaIndex=0;function villaStep(n){villaIndex=(villaIndex+n+villaData.length)%villaData.length;const v=villaData[villaIndex];$('#villaImage').src=v.image;$('#villaImage').alt=v.title.replace('<br>',' ');$('#villaTitle').innerHTML=v.title;$('#villaMeta').textContent=v.meta;$('#villaDescription').textContent=v.description;$('#villaNumber').textContent='0'+(villaIndex+1)+' / 03';updateVillaAction();}$('#previousVilla').onclick=()=>villaStep(-1);$('#nextVilla').onclick=()=>villaStep(1);
$('#menuButton').onclick=()=>{const opened=$('#menu').hidden;$('#menu').hidden=!opened;$('#menuButton').setAttribute('aria-expanded',String(opened));$('#menuButton').setAttribute('aria-label',opened?'Close navigation':'Open navigation');document.body.classList.toggle('menu-open',opened)};$('#menu').onclick=e=>{if(e.target.closest('a,button')){$('#menu').hidden=true;document.body.classList.remove('menu-open');$('#menuButton').setAttribute('aria-expanded','false');$('#menuButton').setAttribute('aria-label','Open navigation')}};

// Keep the still image for visitors who prefer reduced motion.
const heroVideo = $('#heroVideo');
const heroPlayback = $('#heroPlayback');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
let userPaused = false;
function updateHeroPlayback() {
  const playing = !heroVideo.paused;
  heroPlayback.textContent = playing ? 'Pause background' : 'Play background';
  heroPlayback.setAttribute('aria-label', playing ? 'Pause background video' : 'Play background video');
}
async function playHero() {
  if (!heroVideo.getAttribute('src')) heroVideo.src = 'assets/hero-rotation.mp4';
  heroVideo.muted = true;
  try { await heroVideo.play(); } catch { /* Keep the poster if playback is blocked. */ }
  updateHeroPlayback();
}
heroPlayback.hidden = false;
heroPlayback.addEventListener('click', () => {
  if (heroVideo.paused) {
    userPaused = false;
    playHero();
  } else {
    userPaused = true;
    heroVideo.pause();
  }
});
heroVideo.addEventListener('play', updateHeroPlayback);
heroVideo.addEventListener('pause', updateHeroPlayback);
heroVideo.addEventListener('error', () => {
  heroVideo.hidden = true;
  heroPlayback.hidden = true;
});
reducedMotion.addEventListener('change', event => {
  if (event.matches) heroVideo.pause();
  else if (!userPaused) playHero();
});
if (!reducedMotion.matches) playHero();

// The showcase opens real villa pages; breakfast remains a concierge question.
const villaAction = document.querySelector('.villa-copy .text-button');
villaAction.removeAttribute('data-guide');
function updateVillaAction() {
  villaAction.firstChild.textContent = `${villaIndex === 2 ? 'ASK ABOUT BREAKFAST' : 'VIEW VILLA DETAILS'} `;
  if (villaIndex === 2) villaAction.dataset.ask = 'Can breakfast be served on our terrace?';
  else delete villaAction.dataset.ask;
}
villaAction.addEventListener('click', () => {
  if (villaIndex !== 2) {
    window.location.assign(`/villas/${villaIndex === 0 ? 'forest-suite' : 'garden-villa'}`);
  }
});
