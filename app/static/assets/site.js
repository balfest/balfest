(() => {
  "use strict";
  const menu = document.getElementById("mobile-menu");
  if (menu) {
    const summary = menu.querySelector("summary");
    menu.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => { menu.open = false; });
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && menu.open) {
        menu.open = false;
        summary.focus();
      }
    });
    document.addEventListener("click", (event) => {
      if (menu.open && !menu.contains(event.target)) menu.open = false;
    });
  }
  const filters = document.querySelector("[data-filters]");
  if (!filters) return;
  const cards = [...document.querySelectorAll(".program-card[data-category]")];
  const buttons = [...filters.querySelectorAll("[data-filter]")];
  const status = document.getElementById("filter-status");
  filters.hidden = false;
  filters.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-filter]");
    if (!button || !filters.contains(button)) return;
    const selected = button.dataset.filter;
    buttons.forEach((item) => {
      const active = item === button;
      item.classList.toggle("is-active", active);
      item.setAttribute("aria-pressed", String(active));
    });
    let count = 0;
    cards.forEach((card) => {
      card.hidden = selected !== "all" && card.dataset.category !== selected;
      if (!card.hidden) count += 1;
    });
    if (status) status.textContent = "Показано направлений: " + count;
  });
})();
