'use strict';
// Progressive enhancement only. Content, menus and accordions work without JS.
const menu = document.getElementById('mobile-menu');
if (menu) {
  const closeMenu = (focusSummary = false) => {
    menu.open = false;
    if (focusSummary) menu.querySelector('summary').focus();
  };
  menu.querySelectorAll('nav a').forEach((link) => link.addEventListener('click', () => closeMenu()));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && menu.open) closeMenu(true);
  });
  document.addEventListener('click', (event) => {
    if (menu.open && !menu.contains(event.target)) closeMenu();
  });
  const desktop = window.matchMedia('(min-width: 960px)');
  desktop.addEventListener('change', (event) => { if (event.matches) closeMenu(); });
}
// An approved Open Call deadline expires in Moscow time, even on an old build.
document.querySelectorAll('[data-open-call-until]').forEach((section) => {
  const expires = Date.parse(section.dataset.openCallUntil);
  if (Number.isFinite(expires) && Date.now() > expires) {
    section.hidden = true;
    document.querySelectorAll('a[href="#participation"]').forEach((link) => { link.hidden = true; });
  }
});
// Optional analytics: generated config contains no ID until the owner enables it.
const analyticsScript = document.getElementById('analytics-config');
if (analyticsScript) {
  const config = JSON.parse(analyticsScript.textContent);
  const isPublicHost = location.hostname === 'balfest.ru' || location.hostname === 'www.balfest.ru';
  if (config.enabled && /^\d+$/.test(String(config.yandexMetrikaId)) && isPublicHost) {
    window.ym = window.ym || function () { (window.ym.a = window.ym.a || []).push(arguments); };
    window.ym.l = Date.now();
    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://mc.yandex.ru/metrika/tag.js';
    document.head.append(script);
    window.ym(Number(config.yandexMetrikaId), 'init', { clickmap: true, trackLinks: true, accurateTrackBounce: true, webvisor: false });
  }
}
