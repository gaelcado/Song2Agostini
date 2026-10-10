# Installation source isolée

Cette voie installe le projet depuis un checkout Git neuf. Elle ne copie ni audios,
ni partitions, ni références. Les environnements Python ne sont pas des composants
redistribuables d'une application native : ils doivent être construits séparément
sur chaque système. Les bundles natifs suivent `packaging/`.

Prérequis : Python **3.11**, Git et, pour le rendu complet, FFmpeg et MuseScore.
Python 3.12/3.13 ne sont pas implicitement acceptés. `uv` est facultatif ; s'il est
présent, son cache évite de télécharger plusieurs fois les mêmes distributions.
Sans `uv`, le script utilise `venv` et `pip` de Python 3.11.

Depuis la racine du checkout, sur macOS/Linux/WSL :

```sh
python3.11 scripts/bootstrap.py --desktop
```

Dans PowerShell Windows 10/11 x64 :

```powershell
py -3.11 scripts/bootstrap.py --desktop
```

Avec `uv` déjà installé, sur ces systèmes :

```sh
uv run --python 3.11 --no-project scripts/bootstrap.py --desktop
```

`--desktop` ajoute les dépendances figées de la fenêtre native dans l’environnement app. Sans cette option, seule l’interface CLI est installée.

Le script crée exclusivement `work/envs/app`, `work/envs/adtof`,
`work/envs/demucs`, `work/envs/beat_this`, `work/vendor`, `work/models` et ses
journaux. Il n'installe rien dans Python global. ADTOF et Beat This sont récupérés
aux commits de `configs/install/runtime.json`, dans des checkouts détachés ; un
checkout modifié ou un commit différent provoque un arrêt. Les poids ADTOF inclus
dans son dépôt, ainsi que les téléchargements Demucs/Beat This, sont vérifiés par
SHA-256 complet. Un fichier existant incorrect est conservé pour diagnostic.

`configs/install/*.txt` fige la fermeture des dépendances. La paire installée
PyTorch/torchaudio est **2.11.0/2.11.0**, distincte des expériences antérieures
2.14.1/2.11.0. Windows/Linux utilisent les roues CPU du [dépôt officiel
PyTorch](https://download.pytorch.org/whl/cpu), avec version locale `+cpu` ; macOS
utilise les distributions macOS de PyPI. Les bibliothèques CUDA ne sont pas
requises. Cette correction de compatibilité ne démontre aucun gain musical ni
une égalité bit à bit avec les runs antérieurs.

Le worker Demucs conserve les adaptations du projet : décodage FFmpeg en float32,
CPU, quatre threads, seed 0, aucun shift, chargement de son checkpoint vérifié
avant désérialisation de classes. Il contourne les anciennes API de chargement
audio torchaudio ; aucun patch de sources du package Demucs n'est nécessaire.

## Diagnostic et outils natifs

```sh
python3.11 scripts/bootstrap.py --dry-run
python3.11 scripts/bootstrap.py --check
```

Les chemins relatifs deviennent absolus uniquement dans les journaux locaux.
`--source-root CHEMIN` choisit un autre checkout ; `--runtime-root CHEMIN` choisit
l'emplacement des environnements, modèles et outils. Pour exécuter ce runtime,
`DRUM_LAB_RUNTIME_ROOT` doit pointer sur le même dossier.

Le doctor vérifie imports, cohérence des dépendances, hashes des poids et présence
de FFmpeg/MuseScore. Un outil absent signifie que la chaîne complète n'est pas
prête ; le diagnostic est explicite et le code de sortie vaut 1. Les données
techniques sont conservées dans `runtime-install.json` et `bootstrap.log`.
`--allow-missing-tools` est réservé à la validation des moteurs : le JSON conserve
`ready: false` si le rendu reste indisponible. Il ne masque pas un import, une
dépendance ou un hash incorrect.

Les exécutables peuvent être installés sans modification du PATH global sous
`work/tools/ffmpeg.exe` et `work/tools/MuseScore 4/bin/MuseScore4.exe` sous Windows
(avec toutes les DLL et ressources MuseScore), ou sous `work/tools/ffmpeg` et
`work/tools/MuseScore 4.app` sur macOS. FFmpeg peut aussi être sur le PATH ; ses
[liens Windows officiels](https://ffmpeg.org/download.html) désignent les
fournisseurs de builds. MuseScore est disponible via les [releases du projet](https://github.com/musescore/MuseScore/releases).
Le bootstrap ne lance pas d'installateur système et ne réclame pas de privilèges
administrateur. L'installation automatique des outils natifs Windows n'est pas
validée ; déposer seulement un EXE MuseScore sans ses bibliothèques ne suffit pas.
Sous Linux/WSL, l'utilisateur peut fournir les outils de sa distribution ; le
rendu Qt sans écran nécessite la configuration headless du projet.

## Licences et redistribution

ADTOF original : [CC-BY-NC-SA-4.0](https://github.com/MZehren/ADTOF/blob/master/LICENSE).
Le [port PyTorch](https://github.com/xavriley/ADTOF-pytorch) ne contient pas de
licence explicite séparée dans le commit utilisé ; la licence de ses poids
convertis reste non explicitée. Le bootstrap télécharge la source et les poids
pour usage local ; aucune copie de ces poids ou du dépôt vendor n'est incluse
dans Git ni proposée comme composant d'une release publique.

Demucs : [code MIT](https://github.com/adefossez/demucs/blob/main/LICENSE), déclaration
générale MIT du dépôt, aucune notice de poids distincte identifiée ici. Beat This :
[code et poids MIT selon le README](https://github.com/CPJKU/beat_this#license).
FFmpeg dépend de la configuration de son build (LGPL/GPL) ; MuseScore GPL doit
conserver sa propre attribution et ses obligations lors d'une redistribution.
Le manifeste enregistre distinctement licences du code et des poids.

## Preuves locales et portée

Le 10 octobre 2026, l'installation `--only app` a été exécutée dans un nouvel
environnement `work/release-smoke/runtime/envs/app` sur macOS arm64/Python 3.11.14.
Les treize dépendances figées, l'import du package installé et la vérification de
dépendances ont réussi. Ce test n'utilise aucune référence musicale et ne mesure
pas la qualité de transcription. Les validations Windows/Linux doivent provenir
des jobs CI correspondants, pas être extrapolées du Mac.

Installation fraîche des trois moteurs réalisée en 133,92 secondes, avec imports,
checks de dépendances et trois hashes de poids conformes. Preuve :
`work/release-smoke/runtime/runtime-install.json`. FFmpeg résolu sur le PATH ;
MuseScore non copié dans ce runtime distinct : `ready: false` indique explicitement
que le rendu PDF y reste indisponible. Une copie minimale séparée du checkout
(`source-copy`) a également été installée dans `checkout-runtime`, puis les
ressources du wheel ont été résolues depuis `/tmp` : configs et workers présents,
sans dépendre du dossier source original. PySide6 6.8.3 et ses quatre composants
figés ont été installés dans ce second runtime avec `--desktop`.

Le manifeste inclut les versions et déclarations de licence de toutes les
distributions installées, ainsi que les chemins relatifs de leurs notices
(`status: metadata_declaration_only`). Ces métadonnées ne constituent pas une
autorisation légale de redistribution. Le second lancement complet a aussi été
vérifié : les constructions des packages utilisent une archive Git du commit
dans un staging temporaire pour éviter de modifier les sources vendor. Trois
tests d’installation couvrent le plan sans écriture, le refus d’un poids corrompu
sans remplacement, et le diagnostic d’un environnement absent.
