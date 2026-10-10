# Expériences et optimisation

Les deux essais audio complets sur piece_01 sont conservés sous `work/runs/` : mix `20261010T092819-d0f287ce` (échec natif MuseScore) puis Demucs `20261010T092826-05720728` (sorties finales rendues et inspectées par sous-agent isolé). Aucun F1 réel disponible, donc aucune conclusion sur la meilleure méthode ni optimisation de seuil. piece_02 reste réservé au contrôle.

Chaque essai conserve configuration/hypothèse, hashes, source/versions, commande, durée, logs, activations, événements et artefacts. Les échecs comptent dans le budget. `run AUDIO CONFIGS --piece piece_01` ne charge aucune référence. `cycle` orchestre un candidat puis un processus vérificateur et consomme uniquement son retour agrégé ; il s’arrête si référence/couverture manque ou si l’inspection indépendante n’a pas été effectuée.

Le relais Codex consiste à donner à un sous-agent en contexte neuf le dossier figé et les références privées. Son avis public `agent-feedback.json` dans le run contient les hashes des sorties et son statut de lisibilité, sans notes de référence. `verify-final` refuse de réutiliser un avis dont les hashes diffèrent. Après avis et référence évaluable, un score amélioré peut être retenu ; la recherche propose ensuite une seule modification justifiée. Le CLI seul ne crée pas d’agent IA.

Baseline + au plus 12 variantes ciblées, réutilisation des inférences mises en cache, arrêt si entrées de validation insuffisantes ou budget épuisé. Paramètres à geler avant un seul contrôle piece_02. Les scores synthétiques ne sont jamais mélangés au classement musical. Voir `docs/separation.md` et `docs/validation-final-output.md`.

## Suite v3 et reprise

Baselines supplémentaires figées : mix `20261010T094216-38f99831` (rendu lisible accepté), DrumScript `20261010T094832-90460d7c` (intégrité passée, compactage rejeté). Quatre essais enregistrés au total, neuf disponibles ; F1 N/A et aucun meilleur moteur. Rapport `work/research-v3-results.json`.

Après retour du vérificateur, reprendre le candidat en première position de la liste de configurations : `cycle AUDIO CONFIGS --piece piece_01 --resume-run IDENTIFIANT [--reference REFERENCE]`. Cette reprise ne consomme pas un nouvel essai et ne refait pas l’inférence. Elle vérifie audio/configuration/identité, regénère le contrôle final et s’arrête sans référence évaluable ou sans avis indépendant acceptable. Les candidats suivants, s’ils sont autorisés par ces contrôles, consomment chacun un essai. Le classement exclut les scores anciens lorsque le retour courant manque ou est invalidé.

## Diagnostic v4 après retour musicien

Deux essais supplémentaires sur piece_01 : `20261010T102742-6af05201`
(Beat This! pour les premiers temps, mêmes détections ADTOF) et
`20261010T102825-8b369805` (Timbrica kick/snare puis ADTOF, grille historique).
Six essais sur treize consommés ; piece_02 reste intact. Les deux contrôles
finaux d'intégrité passent ; les métriques musicales restent N/A.
La phase améliore un symptôme sur les prédictions (snare au début de mesure
35 → 2) ; le filtre du kit risque de perdre des grosses caisses utiles.
Aucune variante promue comme meilleure ou activée par défaut.

Correction de pagination testée sans nouvelle inférence dans
`work/layout-v4-smoke` : kit trois pages et phase quatre pages acceptés comme
brouillons lisibles, contenus musicaux conservés. Le PDF phase figé trois pages
reste accepté ; la page additionnelle du smoke n'est pas un gain établi.
Ces rendus de présentation ne remplacent pas les runs figés. Le traitement
produit réel utilise le profil historique et reste séparé du classement de
recherche. Rapport courant `work/research-v4-results.json`.

## Phase et gravure v5

Retour utilisateur : convention Agostini et snare trop souvent au premier temps
dès la mesure huit de l'ancienne édition. Nouvelle présentation française
contrôlée séparément sans changement des événements. Unique essai supplémentaire
`20261010T104109-a75f54de` : nettoyage des doubles pics Beat This indépendamment
des notes, cache contrôlé, 77/77 intervalles downbeats de quatre temps, 6,89 s.
Sept essais sur treize consommés, six disponibles ; contrôle intact.
Trois pages acceptées comme brouillon lisible par contexte isolé ; vérification
finale d'intégrité passée. Scores musicaux N/A. Le produit choisit cette grille
audio désormais, sans qualifier le détecteur de meilleur ni forcer de kick.
Le job app généré sans cache de grille fourni est contrôlé séparément ; un échec
MuseScore et sa reprise sont conservés. Voir `docs/audio-grid-v5.md` et l'état
courant dans `docs/STATUS.md`.
