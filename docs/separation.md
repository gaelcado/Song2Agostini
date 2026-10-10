# Contrat entre recherche et vérification

Les partitions manuelles sont exclusivement des références de vérification.
Elles ne sont jamais des exemples, des prompts de transcription, des corrections
à recopier ou des données utilisées pour réentraîner les moteurs.

## Recherche

Entrées autorisées : `data/research-manifest.json`, audios, code des moteurs,
paramètres et feedback agrégé. Sorties : activations, événements, MIDI et notation
dérivée uniquement de l’audio. `run AUDIO CONFIGS --piece piece_01` ne reçoit
aucun chemin de référence et ne charge pas le manifeste complet.

Le sous-agent de recherche ne lit pas `musique/`, `musique IA/`,
`data/raw/scores/`, `data/reference/`, `data/manifest.json` ni
`work/verification/`. L’orchestrateur lui transmet les chemins des copies audio,
pas les dossiers de dépôt contenant aussi les partitions.

## Vérification

Le vérificateur garde les PDF, la numérisation validée humainement, le mapping,
la couverture et l’alignement fixés indépendamment des prédictions. Il compare
une sortie déjà produite et ne la modifie jamais.

Commande : `verify-run REFERENCE work/runs/IDENTIFIANT`.
`evaluate REFERENCE PREDICTION` appartient également à ce rôle : son retour
public est filtré, son rapport complet reste sous `work/verification/`.

Le feedback renvoyé à la recherche contient : précision/rappel/F1,
micro/macro à 50 et 25 ms, TP/FP/FN par instrument, et comptages d’erreurs
par fenêtres de dix secondes à 50 ms. Il ne contient aucun événement de référence,
note manquée exacte, exemple de rythme attendu, alignement de référence,
distance temporelle individuelle ou partition corrigée. Les erreurs détaillées de validation restent aussi côté vérification ; seul un message générique est publié. Les valeurs N/A restent nulles.

## Boucle bornée

Recherche audio → sortie figée → vérification → feedback agrégé → hypothèse
sur une erreur générale → nouvelle recherche audio. La recherche peut utiliser
les scores pour régler des seuils ; ce retour supervisé est explicitement du
développement, pas un test indépendant. Baseline et au plus 12 variantes sur
piece_01 ; paramètres gelés avant un contrôle piece_02.

Lors de nouvelles délégations, créer des contextes distincts sans historique
partagé (`fork_turns="none"`). Fournir à la recherche uniquement ce contrat,
les chemins audio, les paramètres et les feedbacks ; fournir au vérificateur
les références et les sorties figées. Ne pas transférer son audit détaillé à la
recherche. L’orchestrateur peut organiser les échanges sans proposer de notes
à partir des feuilles manuelles.

Ces règles et les interfaces assurent une séparation logique. Les agents de
cette session partagent le système de fichiers : les dossiers dits privés ne
sont pas protégés par un sandbox OS. Ne pas présenter cette organisation comme
une interdiction matérielle de lecture. Les vérifications synthétiques testent
le contrat logiciel, sans fournir de benchmark musical.

## Corpus externe de régression

Les dix cas `bench_01` à `bench_10` utilisent exclusivement
`data/benchmark-research-manifest.json` côté recherche. Les références MIDI
originales, leurs candidates symboliques et les vues de lecture restent dans
le manifeste privé et `work/verification/`. Le supplément batterie seule
`tech_01` à `tech_10` possède ses deux manifestes séparés et ne compte pas parmi
les dix mixes multi-instruments.

`benchmark configs/baseline.json` applique un profil unique figé aux audios,
sans chemin de référence. Chaque sortie est contrôlée dans un processus séparé.
Ce contrôle d'intégrité n'est ni une comparaison musicale ni un avis humain.
La première passe constitue une baseline de développement externe ; elle
n'entame pas les essais de `piece_01` ni le contrôle réservé de `piece_02`.
Les références non validées et non alignées restent non évaluables.

La validation reste dans le chat et les artefacts privés. Le produit ne sert
ni `/verification`, ni ses documents, ni les routes `/api/verification`, même
avec une session valide. Les sources, projections et décisions historiques
sont conservées hors Git ; elles ne sont pas des fonctionnalités du produit.
Les confirmations partielles ne modifient aucune prédiction et ne promeuvent
jamais seules une référence au statut de vérité validée. Les projections
lisibles des MIDI sources restent distinctes des originaux et des sorties.
Le périmètre actuel est fixé dans `docs/handoff-produit-et-simplification.md`.
