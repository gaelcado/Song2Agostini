# Données intégrées — 10 octobre 2026

Les dossiers déposés par l’utilisateur constituent les deux paires audio/partition manuelle.
Les originaux restent intacts ; quatre copies vérifiées par SHA-256 sont disponibles dans `data/raw`.

| Identifiant | Audio déposé | Partition manuelle | Provenance déclarée | Rôle |
| --- | --- | --- | --- | --- |
| piece_01 | musique/Deluxe Michael.MP3 | musique/Michael-Deluxe.pdf | artisanale | développement |
| piece_02 | musique IA/Bacalao con pan Mp3.MP3 | musique IA/Bacalao con pan 02.pdf | Suno | contrôle après gel |

`data/manifest.json`, réservé à la vérification, relie les copies, leurs sources, empreintes, tailles et métadonnées audio locales (ffprobe). `data/research-manifest.json` est sa projection audio seule destinée à la recherche.
Les rôles suivent le protocole existant ; aucune inférence n’a été exécutée sur le contrôle.
Durées conteneur : piece_01 217,940 s ; piece_02 179,958 s. Ce ne sont pas des alignements de partitions.

Rejouer l’import : `.venv/bin/python lab/scripts/prepare_inputs.py`.
Le script conserve les annotations existantes et refuse de remplacer une copie différente.
Originaux, copies, manifeste et sorties restent exclus de Git ; aucun upload audio.

## Références indépendantes

L’audit détaillé des PDF est réservé au vérificateur : `work/verification/reference-review.md`, hors Git. Le sous-agent de recherche ne reçoit ni cet audit, ni les partitions, ni le manifeste complet.
Son contrôle ne remplace pas la validation humaine d’une numérisation exigée par AGENTS.md.
Une référence symbolique avec couverture explicite par instrument, répétitions développées et alignement audio indépendant doit encore être produite et validée.
Les booléens `human_validated` et `alignment_fixed` restent faux ; les références absentes ne sont pas remplacées par des événements fictifs.
Les zones simplifiées/non détaillées restent non évaluables tant que leur couverture n’est pas confirmée.

## Boucle de recherche

Ces données servent à évaluer et régler les moteurs, sans réentraînement de poids à ce stade.
La baseline audio seule de piece_01 est dans `work/predictions/piece_01-baseline` (MIDI brut, JSON, logs, cache, registre).
Elle ne constitue pas un benchmark scoré. Après validation, le runner pourra réutiliser les activations en cache pour la baseline et au plus 12 variantes ciblées.
Figer les paramètres avant toute inférence/évaluation de piece_02. Si les deux morceaux servent aux réglages, déclarer explicitement deux scores de développement.
