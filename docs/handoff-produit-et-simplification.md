# Handoff — périmètre produit et simplification musicale

Décisions explicites de l’utilisateur recueillies dans la conversation latérale
du 10 octobre 2026. Document permanent à lire avant de poursuivre la tâche
principale. Ce handoff ne modifie pas lui-même l’application ni les références.

## Application : le livrable

L’utilisateur demande : « Pas de validation humaine dans l'application.
L'application, c'est le livrable. »

Le parcours produit reste : choisir un audio → générer la partition → aperçu
PDF et téléchargement PDF / MusicXML / MIDI, avec progression et avertissements
compréhensibles sur les hypothèses rythmiques.

Toute validation et vérification doit passer par les interactions dans le chat.
Ne pas proposer au musicien ou à l’élève de qualifier des références, confirmer
une saisie, fixer des alignements ou examiner le protocole de recherche dans
l’application livrée.

Conséquence pour la tâche principale : retirer de l’application le parcours
« Validation humaine », sa navigation et ses accès aux références. Conserver
les originaux, candidates, décisions déjà enregistrées et preuves privées ;
leur inspection doit être organisée depuis le chat avec des artefacts lisibles
(partitions, captures, audio et rapports ciblés). Une vue de comparaison privée
ne doit pas rester accessible comme fonctionnalité du produit.

## Recherche et vérification : séparation conservée

La recherche reçoit uniquement l’audio, les paramètres et le feedback agrégé.
Les partitions manuelles et MIDI sources restent réservés au vérificateur.
Les sous-agents de recherche et de vérification utilisent des contextes
distincts sans historique partagé, conformément à `docs/separation.md`.

Les demandes de confirmation humaine, les passages ambigus et les résultats
de comparaison sont présentés dans le chat. Aucune confirmation ni aucun
alignement ne doit être inventé. Les métriques non évaluables restent N/A.
L’isolement est logique sur un disque partagé, pas une protection par sandbox OS.

## Ce que « simplifier » signifie actuellement

La discussion a distingué les mécanismes suivants dans le code inspecté :

- ADTOF produit cinq familles communes de percussion : grosse caisse, caisse
  claire, charleston, toms et cymbales. La précision des instruments est limitée
  dès la détection ; cela n’est pas une règle pédagogique choisie.
- L’export actuel impose une grille de doubles croches en 4/4. Le swing, les
  triolets et les subdivisions plus fines ne sont pas inférés correctement.
- Les coups du même instrument quantifiés sur le même emplacement sont
  regroupés dans la notation ; les détections restent dans le MIDI brut.
- Le mode compact emploie des reprises pour des blocs strictement identiques
  et regroupe les silences. Il vise la présentation, avec conservation des
  attaques après dépliage, hors regroupements de collisions déjà déclarés.

Exemple inspecté : run `20261010T092826-05720728`, 1 162 coups détectés,
1 147 attaques gravées, 15 collisions regroupées et 78 mesures conservées.
Ces chiffres ne mesurent ni les coups manqués ni les nuances perdues en amont.

L’utilisateur craint une simplification excessive. Le fait que les références
manuelles soient simplifiées pour l’apprentissage définit une politique
d’évaluation, pas à lui seul un algorithme de simplification de la production.
Il n’existe actuellement aucune règle pédagogique complète « conserver le
groove et enlever les ornements » validée par l’utilisateur.

## Proposition discutée, à distinguer des décisions explicites

Une transcription aussi fidèle que possible comme base, accompagnée d’une
édition pédagogique séparée et de règles explicites sur les ornements, breaks
et nuances, a été recommandée dans le chat. Cette architecture n’a pas encore
été explicitement approuvée par l’utilisateur. Ne pas présenter cette
recommandation comme un choix déjà acté, ni décider silencieusement quels
détails musicaux supprimer.

## Actions à reprendre dans la tâche principale

1. Lire ce handoff et intégrer le périmètre produit demandé aux documents actifs.
2. Retirer le parcours de validation de l’application sans supprimer les preuves
   ni interrompre les travaux de recherche utiles en cours.
3. Présenter les vérifications et éventuelles confirmations dans le chat, avec
   des partitions réellement lisibles et les sous-agents isolés prévus.
4. Expliquer les limites de la transcription actuelle et distinguer les pertes
   du moteur, la quantification, les regroupements et la mise en page.
5. Clarifier dans le chat les règles pédagogiques avant d’introduire une
   réduction musicale supplémentaire.

Ce document est le seul changement demandé et réalisé dans cette conversation
latérale ; les modifications du produit restent à exécuter dans la tâche principale.
