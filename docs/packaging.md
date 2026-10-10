# Song2Agostini : applications natives

La fenêtre utilise Qt WebEngine embarqué (PySide6), sans ouverture d’un navigateur externe. Le serveur écoute uniquement sur `127.0.0.1`, sur un port aléatoire. Sessions et contrôles d’origine restent actifs. La fenêtre bloque les requêtes réseau extérieures ; les calculs et l’audio restent locaux. Les téléchargements passent par une boîte de dialogue native. Les traitements sont conservés dans le dossier de données utilisateur, indépendamment de l’installation.

## Construction sur la plateforme cible

Python 3.11 est la cible des builds. Construire Windows sur Windows, macOS sur macOS ; PyInstaller n’effectue pas de compilation croisée. La construction macOS locale porte sur l’architecture de la machine, elle ne certifie pas un binaire universal Intel/Apple Silicon. Les tests Windows CI ne certifient pas à eux seuls toutes les installations Windows 10/11.

```sh
uv venv .venv
uv pip install --python .venv/bin/python '.[desktop,build]'
.venv/bin/python -m drum_lab.desktop --smoke-test
.venv/bin/python packaging/build_desktop.py --preview --dmg
```

Sous Windows utiliser `.venv\Scripts\python.exe`. Omettre `--dmg`. L’exécutable et ses bibliothèques restent ensemble dans `dist/Song2AgostiniPreview/` ; distribuer tout le dossier. Sous macOS l’image est `dist/Song2AgostiniPreview-macos-arm64.dmg` (architecture selon le build), avec une vraie application `.app` et un lien Applications.

**Preview est uniquement une vérification intermédiaire de la fenêtre. Elle ne contient pas les moteurs et ne permet pas une transcription autonome.** Un venv copié depuis le projet ne rendrait pas cet aperçu autonome : les liens Python, chemins editable, modèles et exécutables externes doivent être remplacés ou inclus.

## Runtime complet privé

Les trois environnements d’inférence sont figés séparément : ADTOF, Demucs et Beat This!. Le lanceur principal n’importe pas leurs versions de Torch dans son processus Qt. Chaque worker comprend son interpréteur Python, ses bibliothèques et les données de packages ; le dispatcher accepte les scripts conservés dans les ressources et les interrogations `-c` des adaptateurs.

Le builder fige d’abord la fenêtre Qt, puis copie le runtime intact dans le bundle. Il conserve les noms, liens relatifs et bibliothèques privés des workers et de MuseScore. L’analyse PyInstaller du runtime complet mélangeait les arbres Qt et échouait sur une ressource du bundle MuseScore ; la copie après construction évite ce problème. MuseScore provient d’une copie physique fraîche de l’image officielle, avec sa signature conservée ; le builder signe seulement l’application principale et ne re-signe pas les bundles tiers avec `--deep`. La DMG utilise des liens physiques temporaires quand le système les autorise et une copie normale sinon.

```sh
.venv/bin/python packaging/freeze_workers.py --output work/desktop-runtime/workers
```

Le runtime doit ensuite comprendre `models/demucs`, `models/beat_this`, les poids ADTOF dans son package figé, `tools/ffmpeg`, `tools/ffprobe`, MuseScore et les notices. La prévisualisation PDF utilise QtPdf embarqué. Sur Windows les noms exécutables portent `.exe`. Les binaires FFmpeg macOS de Homebrew ont des dépendances absolues : une simple copie ne suffit pas. Inclure toutes leurs bibliothèques transitives et réécrire leurs chemins, ou fournir un build autonome vérifié. Le script `packaging/bundle_macos_tool.py` copie et relocalise les bibliothèques absolues, puis signe localement ; il refuse les rpaths non résolus. Même contrôle pour MuseScore et les plugins Qt.

L’application cherche les workers dans `runtime/workers/<moteur>/<moteur>[.exe]`. Les modèles et outils proviennent de `DRUM_LAB_RUNTIME_ROOT`. Les scripts et configurations proviennent de `DRUM_LAB_RESOURCE_ROOT` ; PyInstaller les place dans `source/`. `DRUM_LAB_HOME` reste un dossier utilisateur accessible en écriture.

Créer `distribution-manifest.json` dans le runtime. Le manifeste contient `platform`, `architecture`, `self_contained: true`, `offline_smoke_test_passed` (false avant la validation réelle) et `components` avec les clés `adtof`, `demucs`, `beat_this`, `ffmpeg`, `ffprobe`, `musescore`. Chaque composant fournit `path`, `license_path`, `source_offer_path` et une table `sha256` de fichiers relatifs au runtime. Les champs de licence désignent des fichiers réels ; ils ne signifient pas que la redistribution est autorisée. Le build est autorisé avant ce test pour éviter une dépendance circulaire ; il ne certifie l’inférence autonome que si ce test est réussi. Exécuter ensuite audio → PDF/MusicXML hors projet sans Python/ffmpeg/MuseScore du système, conserver les preuves et reconstruire l’image validée. Le manifeste doit aussi conserver les blocages de redistribution identifiés dans l’audit des licences.

```sh
.venv/bin/python packaging/build_desktop.py --runtime-payload work/desktop-runtime --dmg
```

Le build complet produit `dist/Song2Agostini.app` et sa DMG, ou `dist/Song2Agostini/Song2Agostini.exe`. **Les poids/code ADTOF actuellement étudiés ne disposent pas d’une autorisation suffisante de redistribution du port. Les builds contenant ces éléments restent privés ; ne pas les publier en release publique.** Le dépôt et les scripts d’installation peuvent être distribués séparément selon leur licence, en téléchargeant les sources officielles directement sur la machine de l’utilisateur.

Le test complet peut être déclenché directement par l’exécutable figé, avec un audio technique connu (aucune partition de référence). Il charge la vraie fenêtre, puis exécute le même pipeline dans un thread, et conserve `desktop-smoke.json`, les logs et les sorties. Le test de démarrage simple dispose de 20 secondes ; la génération complète de 30 minutes.

```sh
dist/Song2Agostini.app/Contents/MacOS/Song2Agostini --smoke-test \
  --smoke-audio /chemin/absolu/test.wav --smoke-output /chemin/absolu/test-sorties
```

Après un test complet réussi, empaqueter le bundle inchangé et sa preuve externe sans refaire le freeze :

```sh
.venv/bin/python packaging/package_existing_dmg.py --smoke-report /chemin/test-sorties/desktop-smoke.json
```

Le script vérifie les sorties et leurs hashes, la signature du bundle et le rapport de génération audio seule. Il ajoute la preuve externe à la DMG ; le manifeste embarqué conserve honnêtement son statut de candidat avant test. Le renderer macOS est épinglé à MuseScore 4.6.5 après des arrêts natifs répétés de 4.7.5.

Répéter depuis un dossier hors projet, avec `PATH` limité aux outils système, les variables de runtime héritées effacées et un dossier utilisateur temporaire. Le test logiciel n’est pas une mesure de fidélité musicale.

## Licences et validation avant diffusion

Qt/PySide6, Chromium, Python, Torch et leurs dépendances nécessitent leurs notices ; Qt LGPL implique de permettre le remplacement des bibliothèques, et de fournir les informations/sources requises. MuseScore est GPL : joindre les notices et l’accès au code source correspondant au binaire distribué. FFmpeg peut être LGPL ou GPL selon ses options ; conserver sa configuration de compilation et les sources correspondantes. Les licences des poids doivent être vérifiées séparément de celles des moteurs.

Conserver les logs de compilation, hashes, versions et résultats du test hors ligne. Tester sélection audio, génération complète, prévisualisation, PDF multipage, MusicXML et MIDI, téléchargement et fermeture pendant un calcul. Signer et notarier les builds macOS destinés à être distribués ; signer les binaires Windows. Ces signatures ne sont pas disponibles dans un build local sans identité de développeur. Aucun contournement de Gatekeeper/SmartScreen n’est intégré.
