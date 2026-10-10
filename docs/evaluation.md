# Protocole d’évaluation

## Politique v1 historique, avant clarification
Configuration : configs/evaluation.v1.json. Cinq classes communes ; le pitch original reste conservé.
Matching biparti un-à-un : cardinalité maximale puis distance absolue totale minimale, à 50 ms et 25 ms inclusifs.
La couverture de référence est explicite, par classe et intervalle [start,end). Prédictions et références hors couverture sont ignorées et comptées.
Précision, rappel et F1 par classe ; micro sur toutes classes évaluables ; macro sur classes présentes dans la référence.
Une classe sans référence conserve ses faux positifs dans le micro mais reste exclue du macro.
Aucune référence évaluée : agrégats N/A (JSON null), jamais un score parfait. Prédiction vide face à référence non vide : F1=0.
Principal : macro-F1 à 50 ms, accompagné du micro-F1 et du rapport FP/FN horodaté.
Référence musicale réelle : validation humaine obligatoire, couverture et alignement figés avant réglage.
Temps musical, tempo, premiers temps, swing, breaks et sections sont des diagnostics séparés. Leur scoring n'est pas encore implémenté : N/A.
piece_01 : baseline puis au plus 12 variantes, une hypothèse documentée par variante. Choisir avant d'ouvrir piece_02 ; un seul contrôle.
Réutiliser piece_02 pour régler invalide son statut de test indépendant. Deux morceaux ne démontrent pas la généralisation.
Le moteur ne reçoit que l'audio et ses paramètres. Aucun recalage oracle ni correction humaine dans le score automatique.

## Politique v2 — feuilles simplifiées

L’utilisateur confirme que les deux feuilles sont simplifiées pour l’apprentissage. `configs/evaluation.v2.json` fige cette précision avant optimisation. Chaque intervalle de couverture peut déclarer `absence_evaluable: true` seulement lorsque l’absence d’un coup est effectivement annotée/validée comme évaluable. Pour une référence réelle, la valeur par défaut est false ; les fixtures synthétiques gardent leur couverture exhaustive explicite ou conventionnelle.

Les coups de référence explicites sont appariés normalement. Les prédictions supplémentaires hors couverture d’absence évaluable sont comptées dans `unscored_additional`, sans FP automatique. Le rappel des coups explicites peut être calculé avec un alignement validé ; précision/F1 d’une classe restent N/A si leur périmètre n’est pas entièrement évaluable. Les agrégats restent aussi N/A si cette lacune empêche un score comparable. Aucun réglage ne sera retenu sur un F1 non évaluable.
