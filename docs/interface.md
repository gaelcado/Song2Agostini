# Interface locale de transcription

L’atelier propose un parcours audio → génération → aperçu PDF → téléchargement
du PDF, du MusicXML éditable et des deux MIDI. L’aperçu affiche la première page
en image PNG produite localement par `pdftoppm` (Poppler) ; le PDF multipage
complet reste disponible à l’ouverture et au téléchargement. Aucun service audio externe ni
partition de référence n’intervient dans ce parcours. La grille issue de l’audio
reste signalée comme brouillon à vérifier à l’écoute.

Lancer depuis la racine du projet, dans l’environnement isolé :

```sh
.venv/bin/drum-lab serve --port 8765
```

Ouvrir `http://127.0.0.1:8765`. Le serveur utilise uniquement la bibliothèque
standard Python et écoute exclusivement sur la boucle locale IPv4. Les outils
du moteur et `ffprobe` doivent être installés avant une génération réelle.

Les fichiers acceptés sont WAV, FLAC et MP3, de taille non nulle, limités à
200 Mo et 30 minutes. Le contenu et la durée sont contrôlés avec `ffprobe`
avant l’inférence. Le moteur s’exécute en arrière-plan ; les traitements sont
sérialisés (une seule inférence simultanée), avec au plus trois travaux actifs
ou en attente. Le navigateur affiche la progression, conserve le suivi du
traitement dans l’onglet après rechargement et affiche les avertissements
renvoyés par le moteur. Fermer l’onglet n’interrompt pas le calcul local.

Les entrées sont copiées sous `work/ui/jobs/<id>/input.<extension>` ; les
sorties propres à ce traitement sont sous `output/`. Les originaux ne sont
pas modifiés. Ces fichiers restent locaux et ne sont pas supprimés
automatiquement. Les identifiants HTTP ne sont conservés qu’en mémoire : après
un redémarrage du serveur, les anciens traitements ne sont plus accessibles
par l’interface. Les fichiers restent consultables depuis le dossier local.

L’aperçu montre la première page du PDF, rendue localement en PNG par pdftoppm. Un lien ouvre le PDF complet. Cette image est créée à la demande et conservée dans le dossier du traitement ; aucune lecture de référence ne participe à cet aperçu.

L’accès HTTP est limité aux fichiers statiques de l’interface, à cet aperçu et aux quatre
types d’artefacts autorisés d’un travail appartenant à la session du
navigateur. Aucun chemin arbitraire, journal ou répertoire de références n’est
exposé. Les requêtes vérifient Host et Origin ; les créations nécessitent un
jeton de session et son cookie HttpOnly/SameSite. Les erreurs publiques sont
génériques, leurs détails restent dans `error.log` du travail local.
Cette protection concerne l’interface HTTP et ne constitue pas un sandbox OS.

Les tests de `tests/test_ui.py` utilisent un moteur factice et des fichiers
synthétiques. Ils vérifient le téléchargement, l’isolation des sessions,
les limites d’entrée, les origines, les traversées de chemins, les erreurs
privées et la file d’attente. Ils ne valident pas la fidélité musicale du moteur.

La validation et la comparaison avec des références se font dans le chat.
Le serveur produit ne contient plus de route `/verification`, ne sert aucun
asset de cette ancienne vue et ne propose aucune route `/api/verification`.
Ces accès renvoient 403 ou 404, même avec une session valide. Les preuves et
versions de décisions privées restent conservées localement ; voir
[le processus de vérification privé](human-review-interface.md).

Depuis v5, le profil produit choisit explicitement `grid_engine=beat_this` :
premiers temps audio, nettoyage des pulsations doublées, puis gravure française
compatible Agostini. Les environnements et poids Beat This épinglés doivent
être présents ; aucun fallback silencieux vers une phase arbitraire. Le CLI
et ses baselines historiques gardent leur configuration propre. La grille 4/4
reste marquée brouillon, distincte de la convention graphique.

Les titres des audios enregistrés sont retrouvés par empreinte audio à partir
des seuls manifestes de recherche. Les nouveaux audios gardent leur nom de
fichier comme titre. Le titre est affiché après le dépôt, porté dans la partition
et encodé dans le nom du téléchargement ; les IDs techniques ne sont pas des
titres de morceaux. Les anciennes sorties figées ne sont pas renommées.
