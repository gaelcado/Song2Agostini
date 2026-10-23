# Boucle de vérification automatique — octobre 2026

Objectif : ne plus dépendre du seul retour hebdomadaire du musicien pour mesurer
la qualité des partitions. Le vérificateur compare automatiquement une sortie
figée à une référence alignée sur l'audio, puis publie des moyennes.

## Ce qui est mesuré

Pour chaque morceau, sur la sortie réellement livrée (MusicXML expansé, ce que lit
le musicien) :

| Mesure | Question posée |
|---|---|
| Détection 50 ms | Les coups bruts (`events.json`) sont-ils au bon instant, sur le bon instrument ? |
| Écrit 70 ms | Une fois quantifiées, les notes écrites tombent-elles encore au bon instant ? |
| **Mesure + temps** | La note est-elle écrite dans la bonne mesure, au bon temps, sur le bon instrument ? C'est la lecture du musicien. |
| Barres 100 ms | Les barres de mesure sont-elles placées sur les vrais premiers temps ? |
| Mesures identiques | Début et fin de mesure corrects (vérifie aussi 4/4 contre 5/4). |

La position dans la mesure est comparée en fraction de mesure (tolérance d'un
huitième de temps), indépendamment de l'unité écrite (noire, croche pointée…).

## Références

- **Morceaux réels** : partitions PDF saisies à la main par l'agent dans un format
  texte (`data/reference/*.ref.txt`, privé, hors Git) : Perfect Strangers,
  Deluxe Michael (feuille simplifiée de Christophe), Crazy, Heathens. Saisie
  **non validée humainement**. Les passages ambigus (roulements, fills
  illisibles) sont marqués non évalués.
- **GMD tech_01–09** : MIDI originaux joués par des batteurs, audio rendu depuis
  ce MIDI ; alignement exact par construction. Métriques 5/4, 5/8, 6/8, 3/4.
- **OGA bench_02, bench_08** : MIDI de composition, décalage estimé sur l'audio.
  Les autres cas OGA ont un alignement ou une signature MIDI douteux (ex. 2/4
  pour une musique en 4/4) : exclus des moyennes de structure.

L'alignement des références réelles n'utilise jamais les prédictions : suivi
mesure à mesure des enveloppes d'attaques par bandes (grave, médium, aigu) de
l'audio, avec le tempo indiqué sur la feuille.

## Outils

```sh
.venv/bin/python lab/scripts/loop_bench.py NOM 'CONFIG_JSON' --cases ps md crazy heathens tech_01 …
.venv/bin/python lab/scripts/loop_table.py v0-product v1-bars …
.venv/bin/python lab/scripts/score_check.py REF.txt AUDIO RUN      # un morceau réel
.venv/bin/python lab/scripts/midi_check.py MIDI AUDIO RUN           # un cas MIDI
.venv/bin/python lab/scripts/bar_lab.py                             # étude des barres (hors ligne)
.venv/bin/python lab/scripts/threshold_sweep.py RUNS CASE… --sets … # seuils ADTOF (cache)
```

Sorties : `work/research/loop-20261017/` (runs, résultats agrégés),
`work/verification/loop-20261017/` (rapports détaillés privés).

## Limites honnêtes

- L'agent est à la fois chercheur et vérificateur (demande explicite de
  l'utilisateur : travailler seul). La séparation reste logique : réglages
  uniquement sur des moyennes, aucune règle propre à un titre.
- Les références réelles ont été saisies par l'agent ; une erreur de saisie
  fausse le score. Le rapport par mesure permet de les repérer.
- Les feuilles simplifiées (Deluxe Michael) sous-estiment la précision : les
  coups réellement joués mais non écrits comptent comme erreurs.
- Quatre morceaux réels ne prouvent pas la généralisation.

## Passe 1 — 17 octobre 2026 : structure des mesures

Diagnostic de départ (produit `v0`) : la détection des coups est bonne
(micro-F1 ≈ 0,83–0,93), mais la partition écrite est souvent décalée.
La grille comptait les mesures de 4 temps depuis la toute première pulsation,
y compris pendant une intro sans batterie : sur Perfect Strangers, toute la
partition était décalée d'un temps (caisse claire sur 1 et 3), et aucune mesure
de 5/4 n'était possible. Beat This! trouvait pourtant 114/114 premiers temps
réels, avec des pics parasites.

Variantes (une hypothèse chacune, moyennes publiées uniquement) :

| Variante | Hypothèse | Réels mesure+temps | GMD mesure+temps | Décision |
|---|---|---:|---:|---|
| v0 produit | référence | 0,607 | 0,550 | — |
| v1 | mesures de longueur variable par programmation dynamique sur l'activation des premiers temps, longueur dominante apprise du morceau | 0,800 | 0,752 | adoptée |
| v2-cues | + indices de kit (crash/grosse caisse sur le 1, caisse claire seule hors du 1) | **0,822** | 0,751 | adoptée |
| v2-pick | sélection absolue des pics ADTOF (grosse caisse, caisse claire, charleston) | 0,810 | 0,769 | non adoptée : ajoute des caisses claires absentes de la feuille simplifiée, −6 pts sur OGA |
| v3-cues-hh | v2-cues + sélection absolue charleston seul (seuil 0,14) | 0,836 | 0,756 | en réserve : −2 pts Deluxe Michael, −6 pts OGA |
| v3-cues-tuplets | v2-cues + triolets locaux existants | 0,822 | 0,751 | sans effet (la règle s'abstient partout) |

Mesures exactes (début et fin justes) : réels 75 % → 97,5 % ; GMD 67 % → 97 %.
Les mesures 5/4 de Perfect Strangers passent de 0/16 à la majorité.

Affichage : une suite régulière d'au moins quatre coups de cymbale est écrite en
ride (le premier reste crash). Le détecteur n'a qu'une classe « cymbales » ;
cette présentation ne change aucun temps ni aucune métrique.

**Contrôle gelé, Bacalao con pan (piece_02), jamais utilisé pour régler :**
saisi après le gel, évalué une seule fois.

| | Ancien produit | Produit gelé |
|---|---:|---:|
| Mesure + temps (F1) | 0,310 | **0,689** |
| Barres de mesure (F1) | 0,483 | 0,949 |
| Mesures identiques | 41/88 | 81/88 (dont la mesure 2/4) |
| Détection des coups | 0,692 | 0,692 |

Réglage produit retenu (`src/drum_lab/ui.py`, `PRODUCT_CONFIG`) :
`variable_meter`, `drum_downbeat_cues`, `cymbal_streams_as_ride`.

Pistes suivantes, par ordre de gain attendu : charleston manqué (contretemps
masqués par un charleston mi-ouvert ; Bacalao 0,65, Crazy 0,5), caisse claire
de Bacalao (0,70), confusion charleston/cymbale (« (x) » de Crazy à faire
préciser par le batteur), swing et triolets (GMD tech_05/06).

## Passe 2 (en cours) — détection

| Variante | Détection micro (15 cas de dev.) | Remarque |
|---|---:|---|
| batterie isolée (produit) | 0,823 | référence |
| mix complet (`v5-mix`) | 0,824 | Perfect Strangers +3 pts, Crazy −6 pts |
| moyenne des activations mix + isolée | 0,828 | gain faible et inégal ; non adopté |

Constat Bacalao (contrôle, non réglé) : nombreux toms et caisses claires en trop,
probablement les percussions latines rangées par la séparation dans la batterie.
