// Export CSV de la liste de clients (e-mails saisis pour un téléchargement, une commande ou un message).
// Usage : npm run contacts:export > contacts.csv
import { db } from "../server/db.mjs";

const rows = db
  .prepare(
    `SELECT c.email, c.first_source, c.created_at,
            MAX(e.created_at) AS last_activity,
            SUM(e.type = 'download') AS downloads,
            SUM(e.type = 'order') AS orders,
            GROUP_CONCAT(DISTINCT e.slug) AS products
     FROM contacts c LEFT JOIN contact_events e ON e.contact_id = c.id
     GROUP BY c.id ORDER BY c.created_at`,
  )
  .all();

const columns = ["email", "first_source", "created_at", "last_activity", "downloads", "orders", "products"];
const cell = (v) => (v == null ? "" : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
console.log(columns.join(","));
for (const row of rows) console.log(columns.map((c) => cell(row[c])).join(","));
