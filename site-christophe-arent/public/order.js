// Confirmation de commande : attend la confirmation du paiement puis affiche les téléchargements.
(() => {
  const root = document.querySelector(".order-result");
  if (!root) return;
  const id = new URLSearchParams(location.search).get("commande");
  const show = (state) => root.querySelectorAll("[data-state]").forEach((el) => (el.hidden = el.dataset.state !== state));
  const icon = root.dataset.icon;
  const euros = (cents) => (cents / 100).toFixed(2).replace(".", ",") + " €";
  let attempts = 0;

  async function load() {
    try {
      const response = await fetch(`/api/orders/${encodeURIComponent(id)}`);
      if (!response.ok) return show("unknown");
      const order = await response.json();
      if (order.status !== "paid") {
        // Le webhook Stripe peut arriver quelques secondes après la redirection.
        if (++attempts > 15) return show("delayed");
        show("pending");
        return setTimeout(load, 2000);
      }
      root.querySelector(".order-product").textContent = order.product.title;
      root.querySelector(".order-amount").textContent = euros(order.amountCents);
      root.querySelector(".order-ref").textContent = order.id;
      root.querySelector(".order-email").textContent = order.email;
      root.querySelector(".download-buttons").innerHTML = order.links
        .map((l) => `<a class="button" href="${l.url}">${icon}${l.label}</a>`)
        .join("");
      show("paid");
    } catch {
      show("delayed");
    }
  }

  if (!id) show("unknown");
  else load();
})();
