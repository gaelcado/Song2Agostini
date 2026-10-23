"""Génère les pages HTML statiques du site dans public/.

Usage : python3 build.py
"""

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
PUBLIC = ROOT / "public"
PRODUCTS = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
HOME_SELECTION = ["blues-mood", "songologia", "objectif-batterie"]

# Coordonnées affichées dans la section contact (à confirmer avant la mise en ligne).
CONTACT_EMAIL = "contact@christophe-arent.fr"
CONTACT_SUBJECTS = ["Cours", "Collaboration", "Concert", "Partitions et méthodes", "Autre demande"]


def icon(name, size):
    paths = {
        "arrow-up-right": '<path d="M7 7h10v10"></path><path d="M7 17 17 7"></path>',
        "arrow-left": '<path d="m12 19-7-7 7-7"></path><path d="M19 12H5"></path>',
        "download": '<path d="M12 15V3"></path><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><path d="m7 10 5 5 5-5"></path>',
        "search": '<path d="m21 21-4.34-4.34"></path><circle cx="11" cy="11" r="8"></circle>',
        "x": '<path d="M18 6 6 18"></path><path d="m6 6 12 12"></path>',
        "music": '<path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle>',
        "file-text": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"></path><path d="M14 2v4a2 2 0 0 0 2 2h4"></path><path d="M10 9H8"></path><path d="M16 13H8"></path><path d="M16 17H8"></path>',
        "files": '<path d="M20 7h-3a2 2 0 0 1-2-2V2"></path><path d="M9 18a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h7l4 4v10a2 2 0 0 1-2 2Z"></path><path d="M3 7.6v12.8A1.6 1.6 0 0 0 4.6 22h9.8"></path>',
        "book-open": '<path d="M12 7v14"></path><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"></path>',
        "lock": '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path>',
        "gauge": '<path d="m12 14 4-4"></path><path d="M3.34 19a10 10 0 1 1 17.32 0"></path>',
    }
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'class="lucide lucide-{name}" aria-hidden="true">{paths[name]}</svg>'
    )


NEW_TAB = '<span class="visually-hidden"> (nouvel onglet)</span>'


def euros(cents):
    return f"{cents / 100:.2f}".replace(".", ",") + " €"


def on_sale(p):
    return bool(p.get("sale", {}).get("priceCents"))


def chip_icon(label):
    # Icône d'interface associée à chaque format (miniatures, fiches produits, récapitulatif de commande).
    if label == "MP3":
        return "music"
    if "PDF" in label:
        return "file-text"
    if label == "Méthode":
        return "book-open"
    if label.endswith("pages"):
        return "files"
    return "gauge"  # niveau (Débutant…)


def format_items(labels, size=13):
    # Formats avec leur icône ; l'icône est décorative, le texte reste lu.
    return "".join(f"<span>{icon(chip_icon(l), size)}{escape(l)}</span>" for l in labels)


def price(p):
    if p["access"] == "gratuit":
        return "Gratuit"
    if p.get("method"):
        return "Chez l’éditeur"
    return euros(p["sale"]["priceCents"]) if on_sale(p) else "Bientôt disponible"


def img_class(p):
    # Partitions en noir et blanc, livres (méthodes) en couleur.
    return "" if p.get("method") else ' class="sheet"'


def format_label(p):
    return "Méthode" if p.get("method") else " + ".join(p["formats"])


def data_attrs(p):
    # Utilisés par catalogue.js pour filtrer les cartes côté navigateur.
    search = " ".join([p["title"], p["subtitle"], p["description"]])
    return (
        f' data-access="{p["access"]}" data-category="{p["category"]}"'
        f' data-formats="{escape(",".join(p["formats"]))}" data-method="{"1" if p.get("method") else ""}"'
        f' data-search="{escape(search)}"'
    )


def card(p):
    alt = ("Couverture de " if p.get("method") else "Aperçu de la partition ") + p["title"]
    category = "Pédagogie" if p["category"] == "pedagogie" else "Création musicale"
    extra = f'<p>{escape(p["cardNote"])}</p>' if p.get("cardNote") else ""
    # L'image double le lien du titre : elle reste cliquable mais sort de l'ordre de tabulation.
    return (
        f'<article class="product-card"{data_attrs(p)}><a href="/catalogue/{p["slug"]}" class="product-art tint-{p["color"]}" '
        f'tabindex="-1" aria-hidden="true"><span class="format-tag">{format_items(["Méthode"] if p.get("method") else p["formats"])}</span>'
        f'<img{img_class(p)} src="{p["image"]}" alt="{escape(alt)}" loading="lazy"/>'
        f'<span class="open-art">{icon("arrow-up-right", 21)}</span></a>'
        f'<div class="card-meta"><span>{category}</span><span>{price(p)}</span>'
        f'<span class="visually-hidden">Format : {escape(format_label(p))}</span></div>'
        f'<h3><a href="/catalogue/{p["slug"]}">{escape(p["title"])}</a></h3>{extra}</article>'
    )


def contact_section():
    options = "".join(f'<option value="{escape(s)}">{escape(s)}</option>' for s in CONTACT_SUBJECTS)
    field_error = lambda name: f'<p class="field-error" id="{name}-error" hidden></p>'
    return f"""<section class="contact" id="contact" aria-labelledby="contact-title"><div class="contact-intro"><h2 id="contact-title">Contact</h2><a class="text-link" href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></div><form class="contact-form" action="/api/contact" method="post" novalidate><div class="field"><label for="contact-name">Nom</label><input id="contact-name" name="name" type="text" autocomplete="name" required aria-describedby="name-error"/>{field_error("name")}</div><div class="field"><label for="contact-email">E-mail</label><input id="contact-email" name="email" type="email" autocomplete="email" placeholder="nom@exemple.fr" required aria-describedby="email-error"/>{field_error("email")}</div><div class="field field-wide"><label for="contact-subject">Objet</label><select id="contact-subject" name="subject" required aria-describedby="subject-error"><option value="">Choisir un objet</option>{options}</select>{field_error("subject")}</div><div class="field field-wide"><label for="contact-message">Message</label><textarea id="contact-message" name="message" rows="6" required aria-describedby="message-error"></textarea>{field_error("message")}</div><div class="field field-wide"><label class="consent"><input type="checkbox" name="consent" value="oui" required aria-describedby="consent-error"/><span>J’accepte que ces informations servent uniquement à répondre à ma demande. <a href="/informations/#confidentialite">Confidentialité</a></span></label>{field_error("consent")}</div><div class="form-actions field-wide"><button class="button" type="submit">Envoyer le message</button><p class="form-status" role="status"></p></div></form></section>"""


def page(title, main, current="", description=None, scripts=""):
    desc = description or "L’univers musical de Christophe Arent : batterie, percussions cubaines, méthodes, partitions PDF et MP3."
    cur = lambda key: (' aria-current="page"' if current == key else ' aria-current="true"' if current == key + "-child" else "")
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{escape(title)}</title>
<meta name="description" content="{escape(desc)}"/>
<link rel="icon" href="/favicon.svg"/>
<link rel="stylesheet" href="/styles.css"/>
</head>
<body>
<a class="skip" href="#contenu">Aller au contenu</a>
<header class="header container"><a class="brand" href="/">Christophe Arent<span class="visually-hidden">, accueil</span></a><nav aria-label="Navigation principale"><a href="/"{cur("home")}>Accueil</a><a href="/catalogue/"{cur("catalogue")}>Catalogue</a><a href="#contact" class="header-contact">Contact {icon("arrow-up-right", 15)}</a></nav></header>
<main id="contenu" class="{main[0]}">{main[1]}<div class="container">{contact_section()}</div></main>
<footer class="footer container"><a class="footer-name" href="/">Christophe Arent</a><p>© 2026 Christophe Arent</p><nav aria-label="Informations légales"><a href="/informations/#mentions">Mentions légales</a><a href="/informations/#confidentialite">Confidentialité</a><a href="/informations/#vente">Conditions de vente</a></nav></footer>
<script src="/forms.js" defer></script>
<script src="/contact.js" defer></script>
{scripts}</body>
</html>
"""


def home():
    by_slug = {p["slug"]: p for p in PRODUCTS}
    cards = "".join(card(by_slug[s]) for s in HOME_SELECTION)
    entry = lambda href, label: f'<a href="{href}">{label} {icon("arrow-up-right", 18)}</a>'
    main = f"""<section class="hero container"><div class="hero-copy"><h1>Batterie<br/>et percussions</h1><p class="hero-description">Partitions, MP3 et méthodes de Christophe Arent.</p><div class="hero-actions"><a class="button" href="/catalogue/">Explorer le catalogue {icon("arrow-up-right", 18)}</a><a class="hero-bio" href="#biographie">À propos de Christophe</a></div></div><div class="hero-photo"><img src="/images/scene.webp" alt="Christophe Arent à la batterie sur scène" fetchpriority="high"/></div></section><div class="container"><nav class="entry-links" aria-label="Explorer les ressources">{entry("/catalogue/?format=audio-partition", "MP3 et partitions")}{entry("/catalogue/?acces=gratuit", "Ressources gratuites")}{entry("/catalogue/?format=methode", "Mes méthodes")}</nav><section class="selection" aria-labelledby="selection-title"><div class="section-heading"><h2 id="selection-title">À la une</h2><a class="text-link" href="/catalogue/">Voir le catalogue {icon("arrow-up-right", 17)}</a></div><div class="product-grid">{cards}</div></section><section id="biographie" class="biography" aria-labelledby="bio-title"><div class="bio-photo"><img src="/images/christophe.webp" alt="Christophe Arent jouant des congas" loading="lazy"/></div><div class="bio-copy"><h2 id="bio-title">À propos</h2><p>Batteur, percussionniste et enseignant, mon parcours va du rock au jazz, puis aux musiques afro-cubaines. Formé à Nîmes et à l’IMFP de Salon-de-Provence, je partage mon activité entre la scène, le studio et l’enseignement.</p><p>Mes séjours à Cuba nourrissent ma pratique de la batterie, des timbales et des congas. Cette recherche se poursuit avec Son Yuma et dans mes méthodes <em>Timba Drums</em> et <em>Objectif Batterie</em>.</p><a class="text-link" href="/catalogue/?format=methode">Mes méthodes {icon("arrow-up-right", 17)}</a></div></section></div>"""
    return page("Christophe Arent — Batterie & percussions", ("home", main), "home")


def catalogue():
    cards = "".join(card(p) for p in PRODUCTS)
    main = f"""<div class="container catalogue"><div class="catalogue-heading"><h1>Catalogue</h1></div><div class="catalogue-toolbar"><div class="access-tabs" role="group" aria-label="Type d’accès"><button type="button" class="selected" aria-pressed="true" data-acces="">Tout</button><button type="button" aria-pressed="false" data-acces="gratuit">Gratuit</button><button type="button" aria-pressed="false" data-acces="payant">Payant</button></div><span class="result-count" role="status">{len(PRODUCTS)} ressources</span></div><div class="filters"><label class="search">{icon("search", 17)}<input type="search" aria-label="Rechercher dans le catalogue" placeholder="Rechercher" value="" name="recherche"/></label><select name="format" aria-label="Format"><option value="" selected>Tous les formats</option><option value="MP3">MP3</option><option value="PDF">PDF</option><option value="methode">Méthode</option><option value="audio-partition">MP3 et partitions</option></select><select name="categorie" aria-label="Univers"><option value="" selected>Tous les univers</option><option value="pedagogie">Pédagogie</option><option value="creations">Créations musicales</option></select><button class="reset" type="button" hidden>{icon("x", 14)}Réinitialiser</button></div><h2 class="visually-hidden">Résultats</h2><div class="product-grid">{cards}</div><div class="empty" hidden><h2>Aucune ressource ne correspond à ces filtres</h2><button class="button" type="button">Réinitialiser les filtres</button></div></div>"""
    return page("Catalogue — Christophe Arent", ("", main), "catalogue", scripts='<script src="/catalogue.js" defer></script>\n')


def detail(p):
    title = escape(p["title"])
    chips = "".join(f"<span>{icon(chip_icon(c), 14)}{escape(c)}</span>" for c in p["chips"])
    tempo = (
        f'<p class="tempo"><span aria-hidden="true">♩ = {p["tempo"]}</span>'
        f'<span class="visually-hidden">Tempo : {p["tempo"]} à la noire</span></p>'
    ) if p.get("tempo") else ""
    audio = ""
    if p.get("audio"):
        if p.get("excerpt"):
            audio = f'<div class="audio-box"><h2>Extrait · 30 secondes</h2><audio aria-label="Extrait de {title}" controls preload="metadata" src="{p["audio"]}"></audio></div>'
        else:
            audio = f'<div class="audio-box"><audio aria-label="Écouter {title}" controls preload="metadata" src="{p["audio"]}"><a href="{p["audio"]}">Télécharger le MP3</a></audio></div>'

    delivery = p.get("delivery", {})
    if delivery.get("mode") == "free":
        status = "Gratuit" if p["access"] == "gratuit" else "Chez l’éditeur"
        extra = '<p class="availability">Lien d’achat à venir.</p>' if p.get("method") else ""
        obtain = f'<strong class="price">{status}</strong>{extra}{download_block(p)}'
    elif on_sale(p):
        files = " et ".join(f["label"] if f["label"].isupper() else f["label"][0].lower() + f["label"][1:] for f in delivery["files"])
        files = files[0].upper() + files[1:]
        obtain = (
            f'<strong class="price">{price(p)}</strong>'
            f'<p class="availability">{escape(files)}, à télécharger dès le paiement.</p>'
            f'<a class="button" href="/commande/{p["slug"]}/">Acheter {icon("arrow-up-right", 17)}</a>'
        )
    elif p.get("method"):
        obtain = '<strong class="price">Chez l’éditeur</strong><p class="availability">Lien d’achat à venir.</p>'
    else:
        obtain = '<strong class="price">Bientôt disponible</strong><button class="button" type="button" disabled>Vente bientôt ouverte</button>'

    # Les fichiers téléchargeables ne sont plus publics : l'aperçu est l'image de la première page.
    preview = f'<img class="sheet-preview{"" if p.get("method") else " sheet"}" src="{p["image"]}" alt="Première page de {title}" loading="lazy"/>'

    related = "".join(card(o) for o in [o for o in PRODUCTS if o["slug"] != p["slug"]][:3])
    main = f"""<div class="container detail"><a class="back" href="/catalogue/">{icon("arrow-left", 15)}Catalogue</a><section class="detail-grid" aria-labelledby="product-title"><div class="detail-art tint-{p["color"]}"><img{img_class(p)} src="{p["image"]}" alt="Aperçu de {title}"/></div><div class="detail-info"><h1 id="product-title">{title}</h1><div class="chips">{chips}</div><p class="description">{escape(p["description"])}</p>{tempo}{audio}<div class="obtain">{obtain}</div></div></section><section class="preview-section" aria-labelledby="preview-title"><div><h2 id="preview-title">Aperçu</h2></div>{preview}</section><section class="related" aria-labelledby="related-title"><div class="section-heading"><h2 id="related-title">Autres ressources</h2><a class="text-link" href="/catalogue/">Voir le catalogue {icon("arrow-up-right", 17)}</a></div><div class="product-grid">{related}</div></section></div>"""
    scripts = '<script src="/download.js" defer></script>\n' if delivery.get("mode") == "free" else ""
    return page(f"{p['title']} — Christophe Arent", ("", main), "catalogue-child", description=p["description"], scripts=scripts)


def download_block(p):
    # Bouton de téléchargement ; l'e-mail est demandé dans une fenêtre modale (<dialog> natif).
    title = escape(p["title"])
    label = "Télécharger l’extrait gratuit" if p.get("method") else "Télécharger"
    return f"""<button class="button" type="button" data-opens="download-dialog" aria-haspopup="dialog">{icon("download", 17)}{label}</button><dialog class="modal" id="download-dialog" aria-labelledby="download-title" aria-describedby="download-desc"><div class="modal-body"><button class="modal-close" type="button" aria-label="Fermer">{icon("x", 18)}</button><div class="modal-step" data-step="email"><p class="summary-meta">{format_items([f["label"] for f in p["delivery"]["files"]], 12)}</p><h2 id="download-title">{title}</h2><p class="form-note" id="download-desc">Indiquez votre e-mail pour accéder aux fichiers.</p><form class="download-form" data-slug="{p["slug"]}" novalidate><div class="field"><label for="download-email">E-mail</label><input id="download-email" name="email" type="email" autocomplete="email" placeholder="nom@exemple.fr" required autofocus aria-describedby="download-email-error"/><p class="field-error" id="download-email-error" hidden></p></div><div class="form-actions"><button class="button" type="submit" data-busy="Préparation…">Accéder aux fichiers</button><p class="form-status" role="status"></p></div></form></div><div class="modal-step download-ready" data-step="ready" hidden><h2 id="download-ready-title" tabindex="-1">Vos fichiers sont prêts</h2><p class="form-note">Ces liens personnels restent valables 7 jours.</p><div class="download-buttons"></div></div></div></dialog>"""


def steps(current):
    labels = ["Coordonnées", "Paiement", "Téléchargement"]
    items = []
    for i, label in enumerate(labels):
        attrs = ' aria-current="step"' if i == current else ' class="done"' if i < current else ""
        items.append(f'<li{attrs}><span class="step-number">{i + 1}</span>{label}</li>')
    return f'<ol class="steps" aria-label="Étapes de la commande">{"".join(items)}</ol>'


def checkout(p):
    title = escape(p["title"])
    amount = price(p)
    consent = lambda name, text: f'<div class="field"><label class="consent"><input type="checkbox" name="{name}" value="oui" required aria-describedby="{name}-error"/><span>{text}</span></label><p class="field-error" id="{name}-error" hidden></p></div>'
    main = f"""<div class="container checkout"><a class="back" href="/catalogue/{p["slug"]}/">{icon("arrow-left", 15)}{title}</a><h1>Commande</h1>{steps(0)}<p class="notice notice-cancelled" hidden>Paiement annulé. Aucun montant n’a été débité.</p><p class="notice notice-simulation" hidden>Mode démonstration : le paiement est simulé, aucune carte n’est demandée.</p><p class="notice notice-closed" hidden>La vente en ligne est momentanément fermée.</p><div class="checkout-grid"><form class="checkout-form" data-slug="{p["slug"]}" novalidate aria-labelledby="checkout-title"><h2 id="checkout-title">Vos coordonnées</h2><div class="field"><label for="checkout-email">E-mail</label><input id="checkout-email" name="email" type="email" autocomplete="email" placeholder="nom@exemple.fr" required aria-describedby="email-error checkout-note"/><p class="field-error" id="email-error" hidden></p><p class="form-note" id="checkout-note">Le reçu de paiement est envoyé à cette adresse.</p></div><div class="consents">{consent("terms", 'J’accepte les <a href="/informations/#vente">conditions de vente</a>.')}{consent("withdrawal", "Je demande l’accès immédiat aux fichiers et renonce à mon droit de rétractation.")}</div><div class="form-actions"><button class="button" type="submit" data-busy="Redirection vers le paiement…">Payer {amount}</button><p class="form-status" role="status"></p></div><p class="secure-note">{icon("lock", 14)}Paiement sécurisé par Stripe</p></form><aside class="order-summary" aria-labelledby="summary-title"><h2 id="summary-title">Récapitulatif</h2><div class="summary-item"><div class="summary-art tint-{p["color"]}"><img{img_class(p)} src="{p["image"]}" alt=""/></div><div><p class="summary-title">{title}</p><p class="summary-meta">{format_items([f["label"] for f in p["delivery"]["files"]], 12)}</p></div><span class="summary-price">{amount}</span></div><dl class="summary-lines"><div><dt>Téléchargement</dt><dd>Immédiat, après le paiement</dd></div><div class="summary-total"><dt>Total</dt><dd>{amount}</dd></div></dl></aside></div></div>"""
    return page(f"Commande · {p['title']} — Christophe Arent", ("", main), "catalogue-child", scripts='<script src="/checkout.js" defer></script>\n')


def informations():
    main = """<div class="container legal"><h1>Informations légales</h1><p>Ce site est en préparation. Les ventes sont actuellement fermées.</p><section id="mentions"><h2>Mentions légales</h2><p>Les informations légales de l’éditeur du site seront complétées avant l’ouverture au public.</p></section><section id="confidentialite"><h2>Confidentialité</h2><p>Aucun compte visiteur ni outil de mesure d’audience n’est ajouté par ce site. Tout téléchargement, gratuit ou payant, demande une adresse e-mail : elle sert à créer vos liens personnels et à garder une trace de vos téléchargements et commandes. Ce site n’envoie aucun e-mail promotionnel ; seul le reçu de paiement vous est envoyé par Stripe. Les messages envoyés depuis le formulaire de contact servent uniquement à répondre à votre demande. Les paiements sont traités par Stripe ; les informations sur l’hébergement, la durée de conservation et le traitement des données seront précisées avant l’ouverture des ventes.</p></section><section id="vente"><h2>Conditions générales de vente</h2><p>Les conditions de vente seront disponibles avant l’ouverture des achats. Aucun paiement n’est accepté pour le moment.</p></section></div>"""
    return page("Informations légales — Christophe Arent", ("", main))


def order_success():
    states = {
        "pending": ("Confirmation du paiement", '<p>Nous attendons la confirmation de Stripe. Cette page se met à jour toute seule.</p>'),
        "paid": ("Merci pour votre commande", '<p>Paiement de <span class="order-amount"></span> pour <strong class="order-product"></strong> confirmé. Référence : <span class="order-ref"></span>.</p><div class="download-buttons"></div><p class="form-note">Ces liens personnels restent valables 7 jours. Le reçu de paiement est envoyé à <strong class="order-email"></strong>.</p>'),
        "delayed": ("Paiement en cours de traitement", '<p>La confirmation prend plus de temps que prévu. Rechargez cette page dans quelques instants pour accéder à vos fichiers.</p>'),
        "unknown": ("Commande introuvable", '<p>Vérifiez l’adresse de cette page ou écrivez à Christophe depuis le formulaire de contact.</p>'),
    }
    blocks = "".join(
        f'<div data-state="{key}"{"" if key == "pending" else " hidden"}><h1>{h1}</h1>{body}</div>' for key, (h1, body) in states.items()
    )
    main = f"""<div class="container order">{steps(2)}<div class="order-result" role="status" data-icon="{escape(icon("download", 17))}">{blocks}</div><a class="text-link" href="/catalogue/">Retourner au catalogue {icon("arrow-up-right", 17)}</a></div>"""
    return page("Commande — Christophe Arent", ("", main), scripts='<script src="/order.js" defer></script>\n')


def write(rel, html):
    path = PUBLIC / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def main():
    write("index.html", home())
    write("catalogue/index.html", catalogue())
    for p in PRODUCTS:
        write(f"catalogue/{p['slug']}/index.html", detail(p))
    write("informations/index.html", informations())
    for p in PRODUCTS:
        if on_sale(p):
            write(f"commande/{p['slug']}/index.html", checkout(p))
    write("commande/succes/index.html", order_success())
    print(f"Site généré dans {PUBLIC}")


if __name__ == "__main__":
    main()
