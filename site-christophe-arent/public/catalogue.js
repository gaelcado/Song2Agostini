// Filtres du catalogue : accès, format, univers et recherche, synchronisés avec l'URL.
(() => {
  const keys = ["acces", "format", "categorie", "recherche"];
  const tabs = [...document.querySelectorAll(".access-tabs button")];
  const search = document.querySelector('.search input');
  const format = document.querySelector('select[name="format"]');
  const categorie = document.querySelector('select[name="categorie"]');
  const reset = document.querySelector(".reset");
  const count = document.querySelector(".result-count");
  const grid = document.querySelector(".product-grid");
  const empty = document.querySelector(".empty");
  const cards = [...grid.querySelectorAll(".product-card")];

  const normalize = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

  let state = {};

  function readUrl() {
    const params = new URLSearchParams(window.location.search);
    state = Object.fromEntries(keys.map((k) => [k, params.get(k) || ""]));
  }

  function writeUrl() {
    const params = new URLSearchParams();
    keys.forEach((k) => state[k] && params.set(k, state[k]));
    const qs = params.toString();
    window.history.replaceState(window.history.state, "", "/catalogue/" + (qs ? "?" + qs : ""));
  }

  function matches(card) {
    const { acces, format: f, categorie: c, recherche: q } = state;
    const d = card.dataset;
    const formats = d.formats.split(",");
    const isMethod = d.method === "1";
    if (acces && d.access !== acces) return false;
    if (c && d.category !== c) return false;
    if (f) {
      if (f === "methode" ? !isMethod
        : f === "audio-partition" ? isMethod || !formats.some((x) => x === "MP3" || x === "PDF")
        : !formats.includes(f)) return false;
    }
    if (q && !normalize(d.search).includes(normalize(q))) return false;
    return true;
  }

  function render() {
    tabs.forEach((t) => {
      const on = t.dataset.acces === state.acces;
      t.classList.toggle("selected", on);
      t.setAttribute("aria-pressed", String(on));
    });
    if (search.value !== state.recherche) search.value = state.recherche;
    format.value = state.format;
    categorie.value = state.categorie;
    reset.hidden = !keys.some((k) => state[k]);

    let n = 0;
    cards.forEach((card) => {
      const show = matches(card);
      card.hidden = !show;
      if (show) n++;
    });
    grid.hidden = n === 0;
    empty.hidden = n !== 0;
    count.textContent = `${n} ressource${n > 1 ? "s" : ""}`;
  }

  function set(key, value) {
    state = { ...state, [key]: value };
    writeUrl();
    render();
  }

  function clear() {
    state = Object.fromEntries(keys.map((k) => [k, ""]));
    writeUrl();
    render();
  }

  tabs.forEach((t) => t.addEventListener("click", () => set("acces", t.dataset.acces)));
  search.addEventListener("input", () => set("recherche", search.value));
  format.addEventListener("change", () => set("format", format.value));
  categorie.addEventListener("change", () => set("categorie", categorie.value));
  reset.addEventListener("click", clear);
  empty.querySelector("button").addEventListener("click", clear);
  window.addEventListener("popstate", () => { readUrl(); render(); });

  readUrl();
  render();
})();
