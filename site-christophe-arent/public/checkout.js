// Page de commande : coordonnées, acceptation des conditions, puis redirection vers le paiement.
(() => {
  const form = document.querySelector(".checkout-form");
  if (!form) return;
  const { checks, bind, postJson } = window.SiteForms;

  // Retour depuis Stripe après annulation.
  if (new URLSearchParams(location.search).has("annule")) document.querySelector(".notice-cancelled").hidden = false;

  // En local sans clé Stripe, le paiement est simulé : on le signale clairement.
  fetch("/api/config")
    .then((r) => r.json())
    .then(({ paymentMode }) => {
      if (paymentMode === "simulation") document.querySelector(".notice-simulation").hidden = false;
      if (paymentMode === "off") {
        document.querySelector(".notice-closed").hidden = false;
        form.querySelector('button[type="submit"]').disabled = true;
      }
    })
    .catch(() => {});

  bind(
    form,
    {
      email: checks.email,
      terms: checks.checked("Acceptez les conditions de vente pour continuer."),
      withdrawal: checks.checked("Cochez cette case pour recevoir les fichiers dès le paiement."),
    },
    async (data) => {
      const { url } = await postJson("/api/checkout", {
        slug: form.dataset.slug,
        email: data.get("email"),
        terms: data.get("terms") === "oui",
        withdrawal: data.get("withdrawal") === "oui",
      });
      window.location.assign(url);
    },
  );
})();
