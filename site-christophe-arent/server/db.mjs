// Base locale SQLite (node:sqlite) : source de vérité de la liste de contacts,
// des liens de téléchargement, des commandes et des messages.
import { DatabaseSync } from "node:sqlite";
import { mkdirSync } from "node:fs";
import { randomBytes } from "node:crypto";

const STORAGE = new URL("../storage/", import.meta.url);
mkdirSync(STORAGE, { recursive: true });

export const db = new DatabaseSync(new URL("site.db", STORAGE).pathname);
db.exec(`
  PRAGMA journal_mode = WAL;
  PRAGMA foreign_keys = ON;

  CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    first_source TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
  );

  -- Historique : chaque téléchargement, commande ou message.
  CREATE TABLE IF NOT EXISTS contact_events (
    id INTEGER PRIMARY KEY,
    contact_id INTEGER NOT NULL REFERENCES contacts(id),
    type TEXT NOT NULL,
    slug TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
  );
  CREATE INDEX IF NOT EXISTS contact_events_contact ON contact_events(contact_id);

  CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    contact_id INTEGER NOT NULL REFERENCES contacts(id),
    slug TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    currency TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    stripe_session_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    paid_at TEXT
  );

  CREATE TABLE IF NOT EXISTS download_links (
    token TEXT PRIMARY KEY,
    contact_id INTEGER NOT NULL REFERENCES contacts(id),
    order_id TEXT REFERENCES orders(id),
    slug TEXT NOT NULL,
    label TEXT NOT NULL,
    file TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    download_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    contact_id INTEGER NOT NULL REFERENCES contacts(id),
    name TEXT NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
  );
`);

export const token = (bytes = 24) => randomBytes(bytes).toString("base64url");
export const normalizeEmail = (email) => String(email ?? "").trim().toLowerCase();
export const isEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

// Crée ou met à jour un contact (client identifié par son e-mail).
export function upsertContact(email, { source }) {
  const address = normalizeEmail(email);
  db.prepare("INSERT INTO contacts (email, first_source) VALUES (?, ?) ON CONFLICT(email) DO UPDATE SET updated_at = datetime('now')").run(address, source);
  return db.prepare("SELECT * FROM contacts WHERE email = ?").get(address);
}

export function logEvent(contactId, type, slug) {
  db.prepare("INSERT INTO contact_events (contact_id, type, slug) VALUES (?, ?, ?)").run(contactId, type, slug);
}

export function saveMessage(contactId, { name, subject, message }) {
  db.prepare("INSERT INTO messages (contact_id, name, subject, message) VALUES (?, ?, ?, ?)").run(contactId, name, subject, message);
  logEvent(contactId, "message", null);
}
