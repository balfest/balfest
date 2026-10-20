'use strict';

// Close the mobile navigation after choosing a section or pressing Escape.
const menu = document.getElementById('mobile-menu');
if (menu) {
  function closeMenu(restoreFocus = false) {
    menu.open = false;
    if (restoreFocus) menu.querySelector('summary').focus();
  }
  menu.querySelectorAll('nav a').forEach(link => {
    link.addEventListener('click', () => closeMenu());
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menu.open) closeMenu(true);
  });
  document.addEventListener('click', event => {
    if (menu.open && !menu.contains(event.target)) closeMenu();
  });
  window.matchMedia('(min-width: 960px)').addEventListener('change', event => {
    if (event.matches) closeMenu();
  });
}

// Keep an already opened page consistent when a confirmed deadline passes.
function updateParticipation() {
  document.querySelectorAll('[data-open-call-until]').forEach(section => {
    const deadline = Date.parse(section.dataset.openCallUntil);
    if (Number.isFinite(deadline) && Date.now() > deadline) {
      section.hidden = true;
      document.querySelectorAll('a[href="#participation"]').forEach(link => {
        link.hidden = true;
      });
    }
  });
}
updateParticipation();
setInterval(updateParticipation, 60000);
