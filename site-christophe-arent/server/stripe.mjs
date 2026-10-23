// Client Stripe. Sans STRIPE_SECRET_KEY, le paiement passe en mode simulation (hors production).
import Stripe from "stripe";
import { lineItem } from "./catalog.mjs";
import { fulfillOrder } from "./delivery.mjs";

const secretKey = process.env.STRIPE_SECRET_KEY;
const siteUrl = () => (process.env.SITE_URL ?? `http://localhost:${process.env.PORT ?? 4321}`).replace(/\/$/, "");
export const stripe = secretKey ? new Stripe(secretKey) : null;

// "stripe" : vrai paiement ; "simulation" : la commande est marquée payée immédiatement ; "off" : vente fermée.
export const paymentMode = stripe ? "stripe" : process.env.NODE_ENV === "production" ? "off" : "simulation";

export async function createCheckoutSession(product, order, email) {
  return stripe.checkout.sessions.create({
    mode: "payment",
    line_items: [lineItem(product)],
    customer_email: email,
    client_reference_id: order.id,
    metadata: { order_id: order.id, slug: product.slug },
    locale: "fr",
    success_url: `${siteUrl()}/commande/succes/?commande=${order.id}`,
    cancel_url: `${siteUrl()}/commande/${product.slug}/?annule=1`,
  });
}

// Vérifie la signature du webhook ; lève une erreur si elle est invalide.
export function parseWebhook(rawBody, signature) {
  return stripe.webhooks.constructEvent(rawBody, signature, process.env.STRIPE_WEBHOOK_SECRET);
}

export async function handleStripeEvent(event) {
  if (event.type === "checkout.session.completed") {
    const session = event.data.object;
    if (session.payment_status === "paid") fulfillOrder(session.metadata?.order_id);
  }
}
