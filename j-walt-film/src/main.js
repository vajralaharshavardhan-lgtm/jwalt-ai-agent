import { createFilm } from './film/film.js';

const film = createFilm(document.getElementById('film'));
window.film = film;

// Optional browser preview (index.html?preview). Rendering never uses this:
// the renderer calls film.seek(t) directly for every frame.
if (new URLSearchParams(location.search).has('preview')) {
  document.body.classList.add('preview');
  const scrub = document.getElementById('scrub');
  const label = document.getElementById('time');
  const button = document.getElementById('play');
  let playing = false, t0 = 0, start = 0;
  const show = (t) => { film.seek(t); scrub.value = t; label.textContent = `${t.toFixed(2)}s`; };
  film.ready.then(() => show(0));
  scrub.addEventListener('input', () => { playing = false; button.textContent = 'Play'; show(+scrub.value); });
  button.addEventListener('click', () => {
    playing = !playing;
    button.textContent = playing ? 'Pause' : 'Play';
    t0 = +scrub.value; start = performance.now();
    const tick = (now) => {
      if (!playing) return;
      const t = t0 + (now - start) / 1000;
      if (t >= film.duration) { playing = false; button.textContent = 'Play'; show(film.duration - 1 / 60); return; }
      show(t);
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}
