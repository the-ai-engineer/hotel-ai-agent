const $ = s => document.querySelector(s);
const villaData=[{title:'The Forest<br>Suite',meta:'ONE BEDROOM · TWO GUESTS · PRIVATE POOL',image:'assets/suite.png',description:'A one-bedroom villa for two guests, with natural linen, a private pool and forest views.'},{title:'The Garden<br>Villa',meta:'TWO BEDROOMS · FOUR GUESTS · PRIVATE POOL',image:'assets/bedroom-daylight.png',description:'A two-bedroom villa for up to four guests, with a private pool and garden terrace.'},{title:'Terrace<br>Breakfast',meta:'TERRACE SERVICE · REQUEST WITH YOUR HOST',image:'assets/breakfast.png',description:'Fresh fruit, warm pastries, and coffee on your terrace. Ask your host to arrange a breakfast time; availability and any charges require confirmation.'}];let villaIndex=0;function villaStep(n){villaIndex=(villaIndex+n+villaData.length)%villaData.length;const v=villaData[villaIndex];$('#villaImage').src=v.image;$('#villaImage').alt=v.title.replace('<br>',' ');$('#villaTitle').innerHTML=v.title;$('#villaMeta').textContent=v.meta;$('#villaDescription').textContent=v.description;$('#villaNumber').textContent='0'+(villaIndex+1)+' / 03';}$('#previousVilla').onclick=()=>villaStep(-1);$('#nextVilla').onclick=()=>villaStep(1);
$('#menuButton').onclick=()=>{const opened=$('#menu').hidden;$('#menu').hidden=!opened;$('#menuButton').setAttribute('aria-expanded',String(opened));$('#menuButton').setAttribute('aria-label',opened?'Close navigation':'Open navigation');document.body.classList.toggle('menu-open',opened)};$('#menu').onclick=e=>{if(e.target.closest('a,button')){$('#menu').hidden=true;document.body.classList.remove('menu-open');$('#menuButton').setAttribute('aria-expanded','false');$('#menuButton').setAttribute('aria-label','Open navigation')}};

// Keep the still image for visitors who prefer reduced motion.
const heroVideo = $('#heroVideo');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
async function playHero() {
  if (!heroVideo.getAttribute('src')) heroVideo.src = 'assets/hero-rotation.mp4';
  heroVideo.muted = true;
  try { await heroVideo.play(); } catch { /* Keep the poster if autoplay is blocked. */ }
}
heroVideo.addEventListener('error', () => { heroVideo.hidden = true; });
reducedMotion.addEventListener('change', event => {
  if (event.matches) heroVideo.pause();
  else playHero();
});
if (!reducedMotion.matches) playHero();
