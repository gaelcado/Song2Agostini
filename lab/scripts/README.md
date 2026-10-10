# Scripts privés de comparaison

`prepare_inputs.py` prépare les copies privées et manifestes. `import_benchmark.py` importe un corpus autorisé. `render_review.py` et `render_corpus_review.py` préparent les vues des références ; `render_output_review.py` et `sync_output_review.py` ajoutent les PDF des runs figés.

Exécuter depuis la racine avec un environnement de recherche contenant les dépendances nécessaires. Exemple : `.venv/bin/python lab/scripts/import_benchmark.py --config configs/corpus-oga-v1.json`. Les rendus nécessitent notamment Verovio/Pillow/Poppler ; ce ne sont pas les dépendances de l’application musicale.

Ces outils de comparaison accèdent aux références. Ils sont réservés au vérificateur et ne doivent pas servir de prétraitement au moteur. Leur sortie est privée sous `work/verification/`. Appliquer [le contrat de séparation](../../docs/separation.md).

`process_user_inputs.py` est une exception audio seule : une baseline locale
sur un à dix nouveaux audios enregistrés, avec le profil produit figé
Demucs → ADTOF → grille Beat This → MIDI brut/quantifié → MusicXML/PDF.
Il ne reçoit ni partition, ni manifeste privé, ni référence. Le corpus Gmail
identifié comprend cinq nouvelles paires, soit dix fichiers ; les MP3 doivent
être récupérés avant toute inférence.

Préparer `data/new-input-research-manifest.json` avec une liste `pieces`.
Chaque entrée contient `id` (sous-ensemble unique de `user_01` à `user_10`),
`audio` (copie locale sous `data/raw/audio/`), `audio_sha256` et `title`.
Le titre vient du nom audio ou des métadonnées de correspondance confirmées
lors de l'import ; aucun contenu musical noté n'est transmis. Les champs
de références sont refusés. Les originaux sont préservés et aucune donnée
audio n'est envoyée à un service externe.

Depuis la racine et l'environnement Python 3.11 isolé :

```sh
.venv/bin/python lab/scripts/process_user_inputs.py --dry-run
.venv/bin/python lab/scripts/process_user_inputs.py
```

Le précontrôle vérifie tous les fichiers, hashes et durées avant le calcul.
Budget : un profil par audio, deux heures audio cumulées au maximum,
trente minutes de calcul par cas, traitement sériel. Le script refuse une
seconde baseline sur un identifiant déjà traité ; inspecter les sorties
conservées avant une éventuelle reprise distincte. Les reprises natives
MuseScore restent celles, bornées, du pipeline existant.

Journaux et rapport progressif : `work/new-inputs-HORODATAGE/` ; rapport final :
`work/new-inputs-results.json`. Chaque cas donne le chemin de son run figé
sous `work/runs/`. La vérification d'intégrité, la lecture des pages et le
jugement musical restent à confier au vérificateur indépendant. Un succès
logiciel produit un brouillon, sans garantie de fidélité musicale.

Lorsqu'un utilisateur corrige un audio fourni ayant produit un run échoué,
la reprise explicite conserve l'échec et exige un nouvel hash, le même profil
et une unique tentative antérieure. Par exemple, pour remplacer Crazy
envoyé initialement sans batterie :

```sh
.venv/bin/python lab/scripts/process_user_inputs.py --dry-run --only user_01 --replace-input-run 20261010T120452-c92d106b
.venv/bin/python lab/scripts/process_user_inputs.py --only user_01 --replace-input-run 20261010T120452-c92d106b
```

Actualiser d'abord la projection audio du manifeste, conserver le manifeste
initial et documenter la correction d'entrée. Chaque nouveau batch conserve
les copies exactes de son script, de sa configuration et de son manifeste.
Le rapport de correction est `work/new-inputs-replacement-results.json` ;
il ne remplace pas le rapport du premier batch.
