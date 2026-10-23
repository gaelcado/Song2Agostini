# Site Christophe Arent (développement local)

Recréation de https://christophe-arent-musique.arentchris.chatgpt.site/, avec formulaire de contact, téléchargements contre e-mail et parcours d’achat.

- `products.json` : catalogue (`color` = fond pastel, `delivery` = fichiers livrés, `sale` = prix).
- `build.py` : génère les pages HTML dans `public/`.
- `public/` : site statique (styles, scripts, images, MP3 d’écoute dans `public/audio/`).
- `files/` : **fichiers téléchargeables, jamais servis directement** — uniquement via des liens personnels.
- `server/` : serveur Node local (pages, API, base de contacts, livraison, Stripe).
- `storage/` : créé au lancement — base SQLite `site.db` (provisoire, en attendant Stripe).

## Lancer

```sh
npm install
npm run dev   # génère les pages puis sert http://localhost:4321
```

## Parcours

**Gratuit** (Blues Mood, Deluxe Michael, extrait d’Objectif Batterie) : bouton « Télécharger » → fenêtre modale qui demande l’e-mail → les liens s’affichent dans la fenêtre.

**Payant** (Songología) : fiche produit → « Acheter » → `/commande/<produit>/` (e-mail, CGV, renonciation au droit de rétractation) → paiement → `/commande/succes/?commande=…` avec les téléchargements. Le seul e-mail envoyé est le reçu de Stripe.

Mode de paiement (`GET /api/config`) :

| Mode | Quand | Effet |
| --- | --- | --- |
| `simulation` | pas de `STRIPE_SECRET_KEY`, hors production | la commande est marquée payée immédiatement (bandeau « Mode démonstration ») |
| `stripe` | `STRIPE_SECRET_KEY` renseignée | redirection vers Stripe Checkout ; le webhook confirme le paiement |
| `off` | production sans clé | vente fermée |

Liens de téléchargement : personnels, valables 7 jours (`/telecharger/<jeton>`), comptés à chaque téléchargement.

## Liste de clients

Pas de mailing : le site n’envoie aucun e-mail. Chaque e-mail saisi (téléchargement, commande, contact) est enregistré avec l’historique des téléchargements et commandes ; à terme, cette liste sera tenue par Stripe (clients).

```sh
npm run contacts:export > contacts.csv
```

## Brancher Stripe

1. Copier `.env.example` en `.env` et renseigner la clé de test Stripe.
2. `stripe listen --forward-to localhost:4321/api/stripe/webhook`, puis reporter le `whsec_…` dans `.env`.
3. `npm run dev` : le bouton « Payer » redirige vers Stripe Checkout.

## Reste à faire avant la mise en ligne

- Déposer les fichiers complets de Songología dans `files/` (`songologia.mp3`, `songologia.pdf`) et confirmer le prix (9,00 € provisoire).
- Adresse de contact définitive (`CONTACT_EMAIL` dans `build.py`) ; les messages du formulaire sont pour l’instant seulement enregistrés.
- Mentions légales, CGV, durée de conservation des données.
