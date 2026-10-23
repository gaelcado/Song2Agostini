// Livraison des fichiers : liens personnels et temporaires vers files/ (jamais servi directement).
// Le site n'envoie aucun e-mail : les liens s'affichent à l'écran, Stripe envoie le reçu de paiement.
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { db, token, logEvent } from "./db.mjs";
import { findProduct } from "./catalog.mjs";

export const FILES = fileURLToPath(new URL("../files/", import.meta.url));
const LINK_DAYS = 7;

const toLink = (row) => ({ label: row.label, url: `/telecharger/${row.token}` });

function issueLinks(contactId, product, orderId = null) {
  return product.delivery.files.map((f) => {
    const t = token();
    db.prepare(
      `INSERT INTO download_links (token, contact_id, order_id, slug, label, file, expires_at)
       VALUES (?, ?, ?, ?, ?, ?, datetime('now', '+${LINK_DAYS} days'))`,
    ).run(t, contactId, orderId, product.slug, f.label, f.file);
    return toLink({ token: t, label: f.label });
  });
}

// Téléchargement gratuit : liens immédiats.
export function deliverFree(contact, product) {
  const links = issueLinks(contact.id, product);
  logEvent(contact.id, "download", product.slug);
  return links;
}

// Commande payée : idempotent (le webhook Stripe peut être rejoué).
export function fulfillOrder(orderId) {
  const order = db.prepare("SELECT * FROM orders WHERE id = ?").get(orderId);
  if (!order || order.status === "paid") return order;
  db.prepare("UPDATE orders SET status = 'paid', paid_at = datetime('now') WHERE id = ?").run(orderId);
  issueLinks(order.contact_id, findProduct(order.slug), orderId);
  logEvent(order.contact_id, "order", order.slug);
  return db.prepare("SELECT * FROM orders WHERE id = ?").get(orderId);
}

export function orderLinks(orderId) {
  return db.prepare("SELECT token, label FROM download_links WHERE order_id = ? ORDER BY rowid").all(orderId).map(toLink);
}

// Résout un lien : null si inconnu ou expiré ; `missing` si le fichier n'est pas encore déposé.
export function resolveLink(t) {
  const link = db.prepare("SELECT * FROM download_links WHERE token = ? AND expires_at > datetime('now')").get(t);
  if (!link) return null;
  const path = FILES + link.file;
  if (!existsSync(path)) return { ...link, missing: true };
  db.prepare("UPDATE download_links SET download_count = download_count + 1 WHERE token = ?").run(t);
  return { ...link, path };
}
