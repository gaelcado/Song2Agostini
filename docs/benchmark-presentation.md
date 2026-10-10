# Correction de présentation — variante unique v2

Le retour indépendant sur la baseline v1 a rejeté les dix brouillons pédagogiques : absence de légende pour tous, reprise coupée sur un cas et dernières pages peu remplies sur sept cas. L’intégrité technique avait réussi ; fidélité et F1 restent N/A.

Une seule variante de présentation a été exécutée, sans modification des seuils ADTOF, du mix, des événements, de la grille ou de la compression musicale. `configs/presentation-v2.json` ajoute seulement `presentation_version=kit-legend-balanced-pages-v2` au profil de baseline. La convention fixe General MIDI fournit les symboles/positions de la légende, sans référence manuelle.

## Correction

La gravure ajoute une légende visible des instruments présents, leur forme de tête et leur position sur la portée. Les lignes sont espacées et une marge est réservée avant le premier système. Le texte de reprise devient « Jouer N fois » au début du bloc. Les systèmes sont répartis sur les pages de manière équilibrée ; un silence multimesure compte comme une unité visible sans supprimer ses mesures du MusicXML.

Des rendus temporaires `bench_03` (clairsemé) et `bench_10` (dense) ont permis de vérifier les cinq pages avant le lot. Une collision de texte dans la première préproduction a été corrigée dans cette même variante. Les cinq pages suivantes ont été acceptées comme brouillons lisibles par le vérificateur. Ces échantillons ne sont pas des runs ni des sorties de remplacement pour les cas échoués.

Tests ciblés : 17 réussis (`tests/test_engraving.py`, `tests/test_rendering.py`, `tests/test_benchmark.py`). Ils incluent l’équilibre des pages, l’absence de rupture dans les mesures cachées sous les silences multiples, la légende, le texte de reprise et la conservation des événements expansés.

## Résultats figés

Première passe v2 : sept chaînes complètes et trois échecs de rendu natif MuseScore (`bench_02`, `bench_08`, `bench_10`, SIGABRT après trois tentatives). Deux reprises seulement ont été autorisées, sur les mêmes caches/configurations : `bench_02` réussit, `bench_08` échoue encore. Arrêt définitif de cette variante : **huit chaînes complètes, dix cas traités, dix-huit pages PDF finales**, deux PDF non livrables. Les fichiers PDF partiels dans les répertoires échoués ne sont pas acceptés. Aucun PDF v1 ni échantillon temporaire ne remplace un échec v2.

| Cas | Run final v2 | Résultat | Pages finales |
| --- | --- | --- | ---: |
| bench_01 | 20261010T101403-367ea91d | chaîne complète | 1 |
| bench_02 | 20261010T101512-1703fbab | chaîne complète | 2 |
| bench_03 | 20261010T101416-d81ce12d | chaîne complète | 1 |
| bench_04 | 20261010T101420-76c75ef2 | chaîne complète | 2 |
| bench_05 | 20261010T101424-c27fb0af | chaîne complète | 3 |
| bench_06 | 20261010T101431-5294afc2 | chaîne complète | 3 |
| bench_07 | 20261010T101435-ec5f568f | chaîne complète | 3 |
| bench_08 | 20261010T101517-5d15754c | échec PDF natif | N/A |
| bench_09 | 20261010T101449-056cdec9 | chaîne complète | 3 |
| bench_10 | 20261010T101455-45418cdb | échec PDF natif | N/A |

Les empreintes de `events.json`, `raw.mid`, `grid.json` et du MIDI quantifié sont **strictement identiques à la baseline pour les dix cas**, y compris les intermédiaires des deux échecs. Preuve : `work/benchmark-presentation-invariance.json`. Les audits internes MusicXML des huit chaînes complètes valident l’expansion ; la vérification indépendante confirme aussi l’égalité de la grille et de l’expansion MusicXML. Les huit PDF finaux (18 pages) sont acceptés comme brouillons lisibles ; `bench_08` et `bench_10` restent rejetés pour PDF final échoué. Feedback public : `work/benchmark-presentation-feedback.json`. Aucune amélioration de fidélité musicale n’est revendiquée.

## Coût et conservation

Calcul local CPU, inférences mises en cache. Somme des durées de production : 55,46 s pour le lot et 12,55 s pour les deux reprises. Les rendus de préproduction sont supplémentaires et ne font pas partie de ce chronométrage. Les interruptions MuseScore restent un risque technique documenté.

Baseline v1 inchangée : `work/benchmark-v1-final.json`, `work/benchmark-presentation-baseline.json`, `work/benchmark-first-pass.json` et `work/benchmark-retry.json`. Variante : `work/benchmark-presentation-first-pass.json`, `work/benchmark-presentation-retry.json`, `work/benchmark-presentation-results.json`, journaux `work/benchmark-presentation.log` et `work/benchmark-presentation-retry.log`. Le tableau courant `work/benchmark-results.json` contient les dix états v2 réels. Chaque échec original et ses journaux sont conservés ; les reprises portent `previous_failed_run`.

La grille reste brouillon (4/4, doubles croches, premier temps et octave de tempo supposés). Prochaine action : diagnostiquer la stabilité du moteur PDF avant une autre génération. Le verdict indépendant de lisibilité est acquis pour huit cas, sans valider leur fidélité musicale. La boucle s’arrête ici, sans autre optimisation d’événements ni essai musical.
