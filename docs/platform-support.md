# Validation des plateformes

Le support est progressif. Une compilation ou des tests unitaires réussis ne
valident pas une transcription musicale, une interface graphique réelle ou
l'installation sur toutes les éditions du système.

| Cible | Preuve au 10 octobre 2026 | Limite |
| --- | --- | --- |
| macOS Apple Silicon | Source locale Python 3.11.14, MIDI/XML/PDF ; runner macOS 14 Python 3.11.9, 180 tests et smoke installée réussis | PDF runner N/A (MuseScore absent), renderer local parfois SIGABRT |
| Linux Ubuntu 22.04 | Python 3.11.17, 180 tests réussis ; export PDF CI en échec | MuseScore 3 rejette `--no-audio`, correction en cours |
| Windows Server 2022 x64 | Python 3.11.9, 180 tests + imports/page HTTP/MIDI/XML ; preview `.exe` compilée et lancée, capture contrôlée | PDF N/A sans MuseScore ; runtime moteurs distinct encore en cours |
| Windows Server 2025 x64 | Python 3.11.9, 180 tests + imports/page HTTP/MIDI/XML réussis | PDF N/A sans MuseScore ; aucun test Windows client |
| Windows 10 x64 | Non testé sur machine ou VM réelle | Ne pas annoncer support certifié |
| Windows 11 x64 | Non testé sur machine ou VM réelle | Ne pas annoncer support certifié |
| WSL Ubuntu 24.04 | Premier essai en échec (winget absent/ancien WSL) ; MSI Microsoft vérifié ajouté, second essai en cours | Hôte Server 2022 ; WSL Windows 10/11 client reste à tester |

Preuves : [source quatre OS, commit 29ac36b](https://github.com/gaelcado/Song2Agostini/actions/runs/38047515156),
[preview Windows/macOS, commit 0a534ce](https://github.com/gaelcado/Song2Agostini/actions/runs/38047450886),
[WSL corrigé, en cours](https://github.com/gaelcado/Song2Agostini/actions/runs/38047525528),
[runtimes CPU, en cours](https://github.com/gaelcado/Song2Agostini/actions/runs/38047523936).
La chaîne modèle locale dans le runtime fraîchement installé a exécuté les trois
forwards synthétiques en 14,9 s (ADTOF), 4,8 s (Beat This!) et 7,3 s (Demucs).
Ce contrôle ne fournit aucun score de fidélité musicale.


## Contrôles reproductibles

`Platform source tests` installe l'application dans un environnement isolé avec
le bootstrap, contrôle les imports puis exécute les tests synthétiques. Le smoke
utilise des impulsions artificielles et leur MIDI fabriqué par le test : aucune
référence musicale, aucun modèle et aucune inférence réelle. Il contrôle aussi
les assets installés en ouvrant la page HTTP locale. La grille fixe 120 BPM est
une fixture logicielle, jamais une estimation de grille réelle.

Sur Linux, le PDF est obligatoire. Sur les autres runners, si MuseScore est
absent, le JSON garde `pdf: "N/A"` ; MIDI quantifié et MusicXML restent contrôlés.
Le 10 octobre, une répétition locale du rendu macOS a rencontré le SIGABRT
natif MuseScore (mutex/crash database) après les trois tentatives prévues ;
une seule relance distincte a ensuite réussi. Les logs de l'échec restent dans
`work/platform-smoke/notation/` et la relance dans
`work/platform-smoke-retry/`. Ne pas présenter le renderer comme infaillible.

Les preuves synthétiques sont conservées 14 jours dans les artefacts Actions.
La version de MuseScore fournie par le système est enregistrée indirectement
avec la commande, le chemin et le hash du renderer dans `notation.json`.
Les paquets système du runner évoluent : les environnements CI ne sont pas des
images de système entièrement gelées.

`Experimental WSL source smoke` met à jour WSL avec le MSI Microsoft 3.0.1
x64 vérifié par SHA256, puis installe Ubuntu 24.04 avec l’action officielle
Canonical puis teste le commit exact, les unitaires et un véritable export PDF.
Ubuntu 24.04 utilise son Python 3.12 dans un venv ; la matrice native utilise
Python 3.11. Le résultat WSL est distinct d'un résultat Ubuntu natif.

`Build desktop preview` compile un exécutable Windows et un bundle/DMG macOS
**de prévisualisation**, puis lance le binaire compilé avec `--smoke-test`
(fenêtre, chargement HTTP et éléments DOM, capture PNG). Les artefacts publics contiennent uniquement la preuve de build JSON et la
capture PNG ; aucun binaire Qt ni bundle desktop n’est publié en attendant
la vérification des notices et sources de ses dépendances. Ces builds de test
ne contiennent pas les runtimes moteurs
ni les modèles : ils ne constituent pas la distribution autonome complète.

`Full CPU runtime smoke`, manuel et limité à 60 minutes par OS, télécharge les
versions et checkpoints épinglés, vérifie leurs hashes et les imports puis
exécute des forwards CPU ADTOF et Beat This! sur l'audio artificiel. Demucs
exécute aussi un forward si FFmpeg est disponible ; sinon son forward est N/A.
Les logits finis attestent l'exécution, aucune exactitude musicale. Le flag
`--allow-missing-tools` laisse `ready: false` quand FFmpeg/MuseScore manquent,
sans confondre cette installation partielle avec une chaîne PDF complète.
Aucun poids, environnement moteur ni audio privé n'est publié en artefact.

Les actions GitHub sont épinglées à leurs SHA ; les tokens ont seulement
`contents: read`, le checkout ne conserve pas les identifiants et les workflows
n'effectuent aucune publication de Release. L'action WSL est sous licence MIT.
Son installation utilise les dépôts Microsoft/Ubuntu et des paquets système
évolutifs : épingler son code ne fige pas ces paquets. On n'utilise pas son
`wsl-checkout`, qui appelle à ce commit une action imbriquée avec `@main`.

## Validation encore nécessaire sur Windows 10/11

Sur chaque OS client x64 réel, consigner édition/build, CPU/RAM, versions Python
et MuseScore, installation neuve, lancement du `.exe`, page desktop, import WAV,
exports et réouverture PDF/MusicXML, arrêt/reprise et absence d'accès réseau
pour les audios. Répéter en WSL avec la version du noyau et la distribution.
Le téléchargement initial des dépendances et poids nécessite le réseau ;
l'audio et les références ne sont jamais envoyés par ces tests.

Sources : [images officielles des runners GitHub](https://github.com/actions/runner-images),
[actions officielles Ubuntu WSL](https://ubuntu.com/wsl/docs/latest/reference/actions/),
[code MIT de l'action WSL épinglé](https://github.com/Ubuntu/WSL/tree/3b7a6b2a43af18aa541eeee1669ac27656630097/.github/actions).
