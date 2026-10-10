# Drum Transcription Lab — instructions aux agents

## Mission
Construire un laboratoire local de transcription de batterie et d'analyse de structure pour un apprenant. Deux enregistrements et deux partitions de batterie faites à la main seront fournis, avec correspondance un-à-un. Comparer les outils et processus, puis améliorer le score de fidélité sans dégrader la lisibilité pédagogique. Communiquer en français, expliquer les résultats simplement.

## Autonomie
Mettre en place et exécuter les outils locaux nécessaires dans le dossier du projet. Utiliser des environnements isolés, ne pas modifier Python global. Continuer les travaux utiles sans les fichiers; signaler précisément ce qui attend les entrées. Ne pas inventer de résultat ou de partition de référence. Aucun abonnement, achat ou upload audio externe n’est demandé. Les services propriétaires restent des comparateurs optionnels.

## Données et références
- Garder les originaux dans data/raw/audio et data/raw/scores, sans les modifier; les exclure de Git.
- Deux identifiants: piece_01 et piece_02. Un manifeste relie audio, partition, étendue annotée et métadonnées.
- Accepter audio WAV/FLAC/MP3 et partition PDF/image/MusicXML/MuseScore/MIDI. Une référence numérisée doit être vérifiée humainement; l'OCR n'est pas une vérité terrain.
- Déterminer si la partition est exhaustive ou simplifiée pour l'apprentissage. Ne pas pénaliser aveuglément des ghost notes absentes d'une partition simplifiée; séparer les événements explicitement annotés et les zones non évaluables.
- Conserver la référence symbolique originale et son mapping vers cinq classes communes: kick, snare, hi-hat, toms, cymbals. Évaluer séparément les distinctions fines si annotées.
- Séparer temps musical (mesure, temps, subdivision) et temps audio (secondes). Fixer l'alignement de référence indépendamment des prédictions. Documenter anacrouse, swing, changements de tempo et de signature.

## Comparaisons initiales
1. ADTOF-pytorch sur le mix original.
2. ADTOF-pytorch sur batterie isolée avec Demucs; ne pas supposer que l'isolation améliore toujours le résultat.
3. DrumScript comme baseline alternative expérimentale.
4. All-In-One pour tempo, beats, downbeats et sections sur le mix complet.
5. ADTOF Plus / séparation des éléments du kit si les premières erreurs le justifient.
DrumLab peut servir d'interface de travail mais n'est pas un nouveau moteur indépendant de Demucs/ADTOF. Épingler versions et commits. Vérifier les licences du code ET des poids; ADTOF original est CC BY-NC-SA 4.0.

## Évaluation honnête
- Avant optimisation, figer mapping, annotations, métriques et politique de matching dans docs/evaluation.md et une configuration versionnée.
- Matching un-à-un des coups de même classe dans une tolérance initiale de 50 ms; publier aussi 25 ms. Aucun double appariement. Rapporter précision, rappel, micro-F1 et macro-F1 sur classes présentes dans la référence, ainsi que détails par classe.
- Évaluer séparément placement dans les mesures, subdivisions, tempo, premiers temps, swing et breaks lorsque la référence permet de le faire. Les sections couplet/refrain ne sont scorables que si elles sont annotées.
- Score principal provisoire: macro-F1 à 50 ms, accompagné de micro-F1 et de tous les diagnostics. Ne pas mélanger subjectivement lisibilité et événements dans un score opaque. Une mesure non évaluable est N/A, pas zéro ni parfaite.
- Utiliser piece_01 pour réglages, piece_02 comme contrôle après gel des paramètres. Si les deux sont utilisés de façon répétée pour régler, appeler les résultats scores de développement; ils ne sont plus un test indépendant. Pour une validation croisée éventuelle, refaire les réglages dans chaque pli sans fuite. Deux morceaux ne prouvent pas la généralisation.
- Ne jamais injecter des notes de la référence dans la prédiction. Un alignement oracle ou une correction humaine est une analyse distincte, jamais le score automatique.

## Boucle expérimentale
Baseline → diagnostic des faux positifs/négatifs → hypothèse précise → une modification → mesure → conserver ou rejeter. Journaliser les essais, y compris les échecs. Réutiliser les inférences mises en cache pour les balayages de seuils. Prévoir des limites explicites d'essais et une condition d'arrêt; commencer par une baseline et au plus 12 variantes ciblées sur le morceau de développement, puis faire le contrôle. Ne pas lancer de boucle infinie ni d'automatisation récurrente sans demande.

Chaque run doit conserver: identifiant, horodatage, hashes des entrées et références, versions/commit du code, commande, configuration, seed si pertinente, logs, durée, prédictions brutes, sorties quantifiées et métriques. Conserver un classement reproductible et un rapport d'erreurs par instrument et passage. Signaler le coût de calcul.

## Sorties attendues
MIDI brut pour conserver le placement, MIDI quantifié séparé, MusicXML, PDF lisible, JSON des événements, carte de structure horodatée, rapport comparatif. Conserver les intermédiaires hors Git. La meilleure méthode doit produire des sorties à partir d'un nouvel audio sans accès à sa partition de référence.

## Qualité logicielle
Implémenter un évaluateur indépendant des moteurs et des adaptateurs interchangeables. Tester surtout le matching un-à-un, les doublons, les tolérances, les classes absentes, les fichiers vides, les erreurs d'entrée et l'absence de fuite de référence. Les fixtures synthétiques valident le logiciel, elles ne constituent pas un benchmark musical réel. Mettre à jour docs/STATUS.md avec preuves, blocages et prochaine action.

## Séparation des rôles demandée par l’utilisateur
Les feuilles manuelles sont réservées au vérificateur et ne servent jamais d’exemples à la recherche. Appliquer `docs/separation.md`. Le sous-agent de recherche reçoit uniquement audios, paramètres et feedback agrégé ; le sous-agent de vérification conserve les références et les détails d’erreurs. Pour ces délégations, utiliser des contextes distincts sans historique partagé (`fork_turns="none"`). Ne pas renvoyer de notes attendues ou de partition corrigée à la recherche. Cette séparation est logique : ne pas prétendre qu’un sandbox OS protège les fichiers partagés.

## Partition finale
La partition PDF multipage est la sortie principale attendue, accompagnée du MusicXML éditable. Intégrer MIDI brut → grille issue de l’audio → MIDI quantifié → MusicXML → PDF dans les runs. Préserver le placement brut et documenter les hypothèses de quantification ; une grille non validée doit rester marquée brouillon. Ne jamais emprunter la grille ou les notes des références manuelles pour fabriquer la partition de recherche.
