# Archive historique — ancienne interface de validation

Ce parcours a été retiré du produit le 10 octobre 2026. Les routes et commandes de serveur décrites ci-dessous ne donnent plus accès aux documents privés. Ce texte conserve la description antérieure, sans constituer une procédure active.

# Validation humaine dans la mini-app

L’onglet **Validation humaine** ouvre `/verification`, un espace distinct de
la génération audio. La lecture de références reste réservée au vérificateur.
Le pipeline de transcription ne charge ni cette interface, ni ses décisions.

Pour `piece_01`, la source originale est affichée à gauche, la saisie proposée
sur une vraie portée de percussion à droite. Le sélecteur parcourt les huit
systèmes de deux mesures écrites de la page 1. Le zoom agrandit les deux vues;
les trois pages originales sont consultables, mais les pages 2 et 3 n’ont pas
encore de saisie. Les reprises ne sont pas dépliées. Les roulements non résolus
ne sont pas remplacés par des coups inventés.

Le lecteur joue la copie locale des 40 premières secondes. Il ne suit pas la
sélection de mesures : aucun alignement mesure/seconde n’est implicitement
attribué. Les repères entendus peuvent être décrits dans les commentaires.

Huit catégories présentent un choix **Confirmé / À corriger / Incertain** et
un commentaire libre. L’enregistrement crée une nouvelle version JSON dans
`work/verification/ui/decisions/`, liée aux SHA-256 de la saisie et de la source.
L’écran affiche la progression sur la sélection courante. Les versions sont
privées et exclues de Git, comme les autres intermédiaires. Même huit choix
confirmés conservent `human_validated=false` et `alignment_fixed=false` : cela
ne certifie pas la couverture complète, les reprises ni un alignement valide.
Les commentaires proposent des corrections; ils ne modifient pas les notes.

## Préparer localement la vue

```sh
uv pip install --python .venv/bin/python verovio==6.3.0
.venv/bin/python lab/scripts/render_review.py
.venv/bin/drum-lab serve --port 8765
```

La préparation lit uniquement les sources privées et la candidate manuelle;
aucune prédiction moteur n’est consultée. Poppler rend les sources en PNG
2400 pixels; Verovio 6.3.0 transforme la notation MusicXML en SVG. Les valeurs
rationnelles originales sont conservées. Les espaces de voix absentes sont
invisibles; ils n’ajoutent pas de silences audibles. Des silences explicitement
saisis sont affichés. Toute position non représentable produit un avertissement
et reste dans la candidate originale, jamais corrigée arbitrairement.

Une correction de rendu MEI emploie le glyphe SMuFL U+E0B3 pour les croix
cerclées, car l’importeur MusicXML Verovio les transforme en slash
([incident upstream #4314](https://github.com/rism-digital/verovio/issues/4314)).
Cette correction concerne uniquement la forme graphique et ne change pas
les durées, positions ou hypothèses de mapping.

## Limites et sécurité

Le serveur écoute uniquement sur 127.0.0.1. Les documents privés nécessitent
une session locale; les mutations exigent son jeton CSRF. Host/Origin sont
vérifiés. Les documents sont accessibles par identifiant allowlisté, jamais
par un chemin fourni par le navigateur. Les réponses n’exposent pas les chemins
locaux. Les commentaires passent par `textContent` ou les valeurs des champs,
jamais du HTML. Une candidate modifiée invalide la vue jusqu’à sa préparation.
L’audio accepte les plages HTTP de bytes pour permettre la navigation.

La séparation est logique, sans sandbox OS des dossiers partagés. Les tests
synthétiques portent sur le contrat HTTP, les chemins, les hashes, le caractère
partiel des confirmations et la génération préexistante; ils ne constituent
pas une validation musicale.

## Dix morceaux avec MIDI original

Le sélecteur ajoute `bench_01` à `bench_10` depuis le corpus privé préparé.
La provenance (titre, auteur, licence) apparaît avec chaque morceau. Le lecteur
utilise son audio complet. La portée **Lecture partition MIDI source** affiche
uniquement les événements du canal percussion GM 10; le MIDI multivoix original
est téléchargeable exclusivement depuis cet espace privé.

```sh
.venv/bin/python lab/scripts/render_corpus_review.py
```

Cette vue est explicitement une **projection de lecture** : les positions sont
arrondies à la double croche et les valeurs de notes sont des valeurs courtes
conventionnelles. Elle ne remplace ni les ticks originaux, ni les annotations
validées, ni un alignement audio. Les collisions de frappes sur un même instrument
peuvent être fusionnées visuellement et sont signalées; le fichier original reste
inchangé. Les changements de signature sont signalés, la lecture utilise la
signature initiale. Un MIDI sans canal percussion affiche un avertissement et
aucune batterie n’est fabriquée. Les dix paires restent en qualification, sans
validation humaine ni score de fidélité automatique revendiqué.

Les snapshots et décisions sont sélectionnés par identifiant de morceau dans
une allowlist fixe. Chaque morceau conserve sa propre empreinte et ses versions
partielles. Après un remplacement du corpus, relancer la préparation privée;
les décisions liées aux anciennes empreintes ne sont pas réutilisées.

## Résultat moteur déjà produit

Pour afficher une sortie figée, le vérificateur l’enregistre explicitement :

```sh
.venv/bin/python lab/scripts/render_output_review.py piece_01 CHEMIN/score.pdf
```

Le PDF et son aperçu PNG première page sont copiés et hashés dans la vue privée.
Ils apparaissent dans un panneau **Résultat moteur figé**, séparé de la source et
de sa saisie. Le PDF complet reste ouvrable. Aucun appariement de mesures, aucun
alignement oracle et aucun score ne découlent de cet affichage. Même commande
pour `bench_01` à `bench_10` après une inférence réellement terminée.

Les documents rendus (PNG/SVG/audio et sorties figées) ont eux-mêmes des hashes.
Une substitution de document bloque sa lecture et l’enregistrement de décisions;
la préparation doit être relancée. Toutes les sessions locales valides ont accès
à cet espace : il s’agit d’une séparation de parcours et de données vis-à-vis du
pipeline, pas d’un compte vérificateur isolé des autres utilisateurs locaux.

Après une campagne terminée, enregistrer tous ses résultats réels :

```sh
.venv/bin/python lab/scripts/sync_output_review.py
```

Ce script lit `work/benchmark-results.json`. Il ajoute les PDF déjà produits et
signale **Génération échouée : aucun PDF final disponible** pour les cas échoués.
Un échec retire l’ancien PDF éventuel de l’allowlist; aucun résultat périmé ne sert
de remplacement. Relancer la synchronisation après une reprise réellement réussie.
