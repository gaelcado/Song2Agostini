// Serveur local : fichiers de public/, téléchargements protégés et API
// (contact, téléchargements gratuits, commandes, webhook Stripe).
import { createServer } from "node:http";
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { basename, extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";
import { findProduct, sellableProduct } from "./catalog.mjs";
import { db, token, isEmail, normalizeEmail, upsertContact, saveMessage } from "./db.mjs";
import { deliverFree, fulfillOrder, orderLinks, resolveLink } from "./delivery.mjs";
import { stripe, paymentMode, createCheckoutSession, parseWebhook, handleStripeEvent } from "./stripe.mjs";

const PUBLIC = fileURLToPath(new URL("../public/", import.meta.url));
const PORT = Number(process.env.PORT ?? 4321);
const MAX_BODY = 64 * 1024;

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
  ".mp3": "audio/mpeg",
  ".pdf": "application/pdf",
};

// Limite simple par adresse IP sur les formulaires (10 envois par tranche de 10 minutes).
const hits = new Map();
function rateLimited(req) {
  const key = req.socket.remoteAddress;
  const now = Date.now();
  const recent = (hits.get(key) ?? []).filter((t) => now - t < 10 * 60 * 1000);
  recent.push(now);
  hits.set(key, recent);
  return recent.length > 10;
}

function sendPage(res, status, title, message) {
  res.writeHead(status, { "Content-Type": "text/html; charset=utf-8" });
  res.end(`<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${title} — Christophe Arent</title><link rel="stylesheet" href="/styles.css"></head><body><main id="contenu" class="container order"><h1>${title}</h1><p>${message}</p><a class="button" href="/catalogue/">Retourner au catalogue</a></main></body></html>`);
}

function sendJson(res, status, body) {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(body));
}

async function readBody(req) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > MAX_BODY) throw Object.assign(new Error("Requête trop volumineuse"), { status: 413 });
    chunks.push(chunk);
  }
  return Buffer.concat(chunks);
}

async function readJson(req) {
  try {
    return JSON.parse((await readBody(req)).toString("utf8") || "{}");
  } catch (error) {
    if (error.status) throw error;
    throw Object.assign(new Error("JSON invalide"), { status: 400 });
  }
}

const routes = {
  "GET /api/config": async (req, res) => sendJson(res, 200, { paymentMode }),

  "POST /api/contact": async (req, res) => {
    if (rateLimited(req)) return sendJson(res, 429, { error: "Trop de demandes" });
    const { name = "", email = "", subject = "", message = "", consent } = await readJson(req);
    const valid = name.trim() && isEmail(normalizeEmail(email)) && subject && message.trim() && consent;
    if (!valid) return sendJson(res, 422, { error: "Champs manquants ou invalides" });
    const contact = upsertContact(email, { source: "contact" });
    saveMessage(contact.id, { name: name.trim(), subject, message: message.trim() });
    // TODO : transmettre aussi le message à Christophe par e-mail.
    console.log(`[contact] ${name.trim()} <${contact.email}> — ${subject}`);
    sendJson(res, 202, { ok: true });
  },

  // Téléchargement gratuit : e-mail obligatoire.
  "POST /api/downloads": async (req, res) => {
    if (rateLimited(req)) return sendJson(res, 429, { error: "Trop de demandes" });
    const { slug, email = "" } = await readJson(req);
    const product = findProduct(slug);
    if (product?.delivery?.mode !== "free") return sendJson(res, 404, { error: "Ressource introuvable" });
    if (!isEmail(normalizeEmail(email))) return sendJson(res, 422, { error: "Adresse e-mail invalide" });
    const contact = upsertContact(email, { source: `download:${slug}` });
    const links = deliverFree(contact, product);
    sendJson(res, 200, { email: contact.email, links });
  },

  // Commande : crée la commande puis renvoie l'adresse de paiement (Stripe) ou de confirmation (simulation).
  "POST /api/checkout": async (req, res) => {
    if (rateLimited(req)) return sendJson(res, 429, { error: "Trop de demandes" });
    if (paymentMode === "off") return sendJson(res, 503, { error: "Vente fermée" });
    const { slug, email = "", terms, withdrawal } = await readJson(req);
    const product = sellableProduct(slug);
    if (!product) return sendJson(res, 404, { error: "Produit indisponible à la vente" });
    if (!isEmail(normalizeEmail(email)) || !terms || !withdrawal) return sendJson(res, 422, { error: "Champs manquants ou invalides" });

    const contact = upsertContact(email, { source: `order:${slug}` });
    const order = { id: token(12), slug, amount: product.sale.priceCents, currency: product.sale.currency ?? "eur" };
    db.prepare("INSERT INTO orders (id, contact_id, slug, amount_cents, currency) VALUES (?, ?, ?, ?, ?)").run(order.id, contact.id, slug, order.amount, order.currency);

    if (paymentMode === "stripe") {
      const session = await createCheckoutSession(product, order, contact.email);
      db.prepare("UPDATE orders SET stripe_session_id = ? WHERE id = ?").run(session.id, order.id);
      return sendJson(res, 200, { url: session.url });
    }
    fulfillOrder(order.id);
    sendJson(res, 200, { url: `/commande/succes/?commande=${order.id}` });
  },

  "POST /api/stripe/webhook": async (req, res) => {
    if (!stripe || !process.env.STRIPE_WEBHOOK_SECRET) return sendJson(res, 503, { error: "Webhook non configuré" });
    let event;
    try {
      event = parseWebhook(await readBody(req), req.headers["stripe-signature"]);
    } catch {
      return sendJson(res, 400, { error: "Signature invalide" });
    }
    await handleStripeEvent(event);
    sendJson(res, 200, { received: true });
  },
};

// Routes à paramètre : /api/orders/:id, /telecharger/:token
async function dynamicRoute(req, res, url) {
  const { pathname } = url;
  if (req.method === "GET" && pathname.startsWith("/api/orders/")) {
    const order = db.prepare("SELECT * FROM orders WHERE id = ?").get(pathname.slice("/api/orders/".length));
    if (!order) return sendJson(res, 404, { error: "Commande introuvable" }), true;
    const product = findProduct(order.slug);
    const email = db.prepare("SELECT email FROM contacts WHERE id = ?").get(order.contact_id).email;
    sendJson(res, 200, {
      id: order.id,
      status: order.status,
      email,
      amountCents: order.amount_cents,
      product: { slug: product.slug, title: product.title },
      links: order.status === "paid" ? orderLinks(order.id) : [],
    });
    return true;
  }
  if (req.method === "GET" && pathname.startsWith("/telecharger/")) {
    const link = resolveLink(pathname.slice("/telecharger/".length));
    if (!link) return sendPage(res, 410, "Lien expiré", "Ce lien de téléchargement n’est plus valable. Demandez-en un nouveau depuis la page de la ressource."), true;
    if (link.missing) return sendPage(res, 404, "Fichier bientôt disponible", "Ce fichier n’est pas encore en ligne. Votre lien reste valable : réessayez plus tard."), true;
    const info = await stat(link.path);
    res.writeHead(200, {
      "Content-Type": TYPES[extname(link.path)] ?? "application/octet-stream",
      "Content-Length": info.size,
      "Content-Disposition": `attachment; filename="${basename(link.path)}"`,
      "Cache-Control": "private, no-store",
    });
    createReadStream(link.path).pipe(res);
    return true;
  }
  return false;
}

async function serveStatic(req, res, pathname) {
  const path = normalize(join(PUBLIC, decodeURIComponent(pathname)));
  if (!path.startsWith(PUBLIC.replace(/\/$/, ""))) return sendJson(res, 403, { error: "Accès refusé" });
  let file = path;
  let info = await stat(file).catch(() => null);
  if (info?.isDirectory()) {
    // Adresses propres : /catalogue → /catalogue/ → catalogue/index.html
    if (!pathname.endsWith("/")) {
      res.writeHead(301, { Location: pathname + "/" + (req.url.split("?")[1] ? "?" + req.url.split("?")[1] : "") });
      return res.end();
    }
    file = join(file, "index.html");
    info = await stat(file).catch(() => null);
  }
  if (!info?.isFile()) {
    res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    return res.end("Page introuvable");
  }
  // no-cache : le navigateur revalide à chaque chargement, les modifications locales s'affichent tout de suite.
  res.writeHead(200, {
    "Content-Type": TYPES[extname(file)] ?? "application/octet-stream",
    "Content-Length": info.size,
    "Cache-Control": "no-cache",
  });
  if (req.method === "HEAD") return res.end();
  createReadStream(file).pipe(res);
}

createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");
  const { pathname } = url;
  try {
    const route = routes[`${req.method} ${pathname}`];
    if (route) return await route(req, res);
    if (await dynamicRoute(req, res, url)) return;
    if (pathname.startsWith("/api/")) return sendJson(res, 404, { error: "Route inconnue" });
    if (req.method !== "GET" && req.method !== "HEAD") return sendJson(res, 405, { error: "Méthode non autorisée" });
    await serveStatic(req, res, pathname);
  } catch (error) {
    console.error(error);
    if (!res.headersSent) sendJson(res, error.status ?? 500, { error: error.status ? error.message : "Erreur serveur" });
  }
}).listen(PORT, () => {
  console.log(`Site sur http://localhost:${PORT} — paiement : ${paymentMode}`);
});
