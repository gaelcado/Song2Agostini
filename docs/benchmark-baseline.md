# Baseline publique — dix mixes complets

Exécution du 10 octobre 2026, recherche exclusivement audio selon `docs/separation.md`. Le corpus admis contient dix audios synthétisés multi-instruments publiés par leurs auteurs, totalisant 967,54 s (16 min 08 s). Il sert à une régression technique ; il ne remplace pas les deux enregistrements de l’apprenant.

Un seul profil figé a été exécuté : ADTOF sur mix complet, sans Demucs, seuils kick/snare/hi-hat/toms/cymbals 0,22/0,24/0,32/0,22/0,30, présentation compacte. Commande : `.venv/bin/drum-lab benchmark configs/baseline.json`. Les dix copies audio ont passé le contrôle de hash avant inférence. Hash du manifeste : `baafd988de1006c176aedbdf1f31d8a6507bd3622db470d9d5ab8f649244b783`.

## Résultat technique

Première passe : 9 chaînes complètes sur 10. `bench_02` a conservé ses événements, MIDI brut, grille audio, MIDI quantifié et MusicXML, mais MuseScore a échoué lors du rendu PDF après trois tentatives natives (SIGABRT, erreur de mutex). Le PDF partiel de cet essai n’est pas une sortie acceptée.

Une seule reprise du même profil, autorisée après diagnostic, a réussi pour `bench_02` grâce aux mêmes activations mises en cache. Aucun seuil, note ou hypothèse musicale n’a changé. L’essai original reste intact ; `bench_02` a deux essais sur le budget de treize, les autres un. Résultat final : **10 chaînes complètes, 10 contrôles d’intégrité réussis, 25 pages PDF, 3 386 événements bruts**. Le statut des runs demeure `awaiting_verification` ; le contrôle technique ne valide ni fidélité musicale ni lisibilité humaine.

| Cas | Run final | Coups bruts | Pages PDF | Déplacement médian, ms | Déplacements >50 ms | Collisions de grille |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| bench_01 | 20261010T100834-59ea915f | 426 | 1 | 44.3 | 90 | 11 |
| bench_02 | 20261010T101031-1a25fd68 | 524 | 2 | 37.3 | 167 | 24 |
| bench_03 | 20261010T100850-d716c901 | 42 | 1 | 46.5 | 15 | 0 |
| bench_04 | 20261010T100856-4fc6c3b9 | 410 | 2 | 44.4 | 97 | 3 |
| bench_05 | 20261010T100906-c9d31eda | 137 | 4 | 36.3 | 11 | 0 |
| bench_06 | 20261010T100917-39ddfc25 | 120 | 3 | 30.2 | 5 | 0 |
| bench_07 | 20261010T100926-2a68004a | 306 | 3 | 28.9 | 24 | 0 |
| bench_08 | 20261010T100936-4ea7da81 | 129 | 2 | 38.6 | 15 | 0 |
| bench_09 | 20261010T100946-39bd3893 | 478 | 3 | 54.5 | 264 | 86 |
| bench_10 | 20261010T100953-8ab57967 | 814 | 4 | 42.8 | 29 | 3 |

Les MIDI quantifiés conservent les comptages d’événements. Les collisions indiquent que plusieurs événements arrivent au même emplacement de grille ; elles ne constituent pas une preuve de faux positifs. Au total, 717 coups sont déplacés de plus de 50 ms et 127 collisions sont signalées. `bench_09` concentre 264 de ces grands déplacements et 86 collisions : c’est un diagnostic de quantification audio, sans comparaison à des notes attendues. Le MusicXML et le MIDI quantifié concordent en temps relatif dans l’audit logiciel (erreur maximale <0,001 ms), sous réserve de l’offset audio documenté.

## Fidélité et présentation

Précision, rappel, micro-F1 et macro-F1 à 25/50 ms : **N/A**. Aucune référence indépendante validée n’a été transmise à la recherche ou utilisée. Aucun meilleur moteur ne peut être nommé avec un profil unique. Les dix retours publics indiquent `requires_independent_review` pour la revue visuelle : aucun PDF n’est déclaré accepté comme partition lisible sur la seule base de ces contrôles.

Chaque run final conserve événements JSON, MIDI brut, grille JSON estimée depuis le mix, MIDI quantifié, MusicXML éditable, PDF, logs, hashes et provenance. La grille demeure brouillon : signature 4/4 et premier temps supposés, résolution à la double-croche, ambiguïté d’octave de tempo ; swing, triolets et changements de signature ne sont pas inférés. Les tempos locaux et offsets ne sont pas des annotations humaines validées. Il n’y a pas de carte couplet/refrain issue d’All-In-One dans cette baseline ; la grille de pulsations ne remplit pas ce rôle.

## Coût, preuves et suite

Calcul local sur CPU, sans upload audio. Somme des durées de production de première passe : 81,58 s ; reprise : 5,46 s de production et 5,94 s murales avec contrôle indépendant. Ce coût inclut transcription, grille et gravure ; il ne mesure pas séparément chaque étape et ne prétend pas représenter un temps d’installation ni une inférence froide garantie. Les activations sont conservées en cache.

Preuves : `work/benchmark-baseline.log`, `work/benchmark-first-pass.json`, `work/benchmark-retry.json`, tableau final dix cas `work/benchmark-results.json`, et les répertoires `work/runs/<run_id>/`. Les échecs et provenance restent accessibles ; le run final de `bench_02` porte `previous_failed_run=20261010T100841-4ed691cb`.

Prochaine hypothèse à examiner, sans lancer d’optimisation : une grille fixe en doubles-croches peut déplacer excessivement des attaques lorsque la pulsation estimée est ambiguë. Priorité à la revue indépendante des brouillons et à la validation de grille depuis l’audio. Une comparaison de moteurs et un classement de fidélité attendent des références vérifiées séparément. Aucun autre profil ni boucle de réglages n’a été lancé.
