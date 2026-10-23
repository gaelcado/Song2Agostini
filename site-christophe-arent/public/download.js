// Téléchargement gratuit : le bouton ouvre une fenêtre modale qui demande l'e-mail,
// puis affiche les liens personnels dans la même fenêtre.
(() => {
  const dialog = document.getElementById("download-dialog");
  if (!dialog) return;
  const trigger = document.querySelector('[data-opens="download-dialog"]');
  const form = dialog.querySelector(".download-form");
  const ready = dialog.querySelector('[data-step="ready"]');
  const { checks, bind, postJson } = window.SiteForms;
  const icon = trigger.querySelector("svg").outerHTML;

  trigger.addEventListener("click", () => dialog.showModal());
  dialog.querySelector(".modal-close").addEventListener("click", () => dialog.close());
  // Un clic sur le fond (hors du contenu) ferme la fenêtre ; Échap est géré par <dialog>.
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener("close", () => trigger.focus());

  bind(form, { email: checks.email }, async (data) => {
    const result = await postJson("/api/downloads", { slug: form.dataset.slug, email: data.get("email") });
    ready.querySelector(".download-buttons").innerHTML = result.links
      .map((l) => `<a class="button" href="${l.url}">${icon}${l.label}</a>`)
      .join("");
    dialog.querySelector('[data-step="email"]').hidden = true;
    ready.hidden = false;
    dialog.setAttribute("aria-labelledby", "download-ready-title");
    dialog.removeAttribute("aria-describedby");
    ready.querySelector("h2").focus();
  });
})();
