// Catalogue côté serveur : même source que le site statique (products.json).
import { readFileSync } from "node:fs";

const products = JSON.parse(readFileSync(new URL("../products.json", import.meta.url), "utf8"));

export function findProduct(slug) {
  return products.find((p) => p.slug === slug) ?? null;
}

// Un produit est vendable quand `sale.priceCents` est renseigné (montant affiché sur le site).
export function sellableProduct(slug) {
  const product = findProduct(slug);
  const sale = product?.sale;
  if (!sale?.priceCents) return null;
  return product;
}

// Ligne de commande Stripe Checkout : un Price existant si configuré, sinon un prix à la volée.
export function lineItem(product) {
  const { sale } = product;
  if (sale.stripePriceId) return { price: sale.stripePriceId, quantity: 1 };
  return {
    quantity: 1,
    price_data: {
      currency: sale.currency ?? "eur",
      unit_amount: sale.priceCents,
      product_data: { name: product.title, description: product.subtitle },
    },
  };
}
