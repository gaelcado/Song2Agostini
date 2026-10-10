# Installer Song2Agostini

Cette version s’installe depuis les sources. Prévoyez Python **3.11**, Git, plusieurs gigaoctets d’espace libre et une connexion pour télécharger les dépendances et modèles. La transcription fonctionne ensuite localement sur le processeur ; un GPU n’est pas nécessaire.

## Mac ou Linux

Clonez le projet puis installez l’application et ses moteurs :

```sh
git clone https://github.com/gaelcado/Song2Agostini.git
cd Song2Agostini
python3.11 scripts/bootstrap.py --desktop
```

Installez aussi FFmpeg et MuseScore depuis leurs distributions officielles. Le contrôle suivant indique les composants manquants :

```sh
python3.11 scripts/bootstrap.py --check --desktop
work/envs/app/bin/drum-lab-desktop
```

Sous Linux, la fenêtre Qt peut nécessiter les bibliothèques graphiques du système. Les détails figurent dans [l’installation technique](docs/installation-technique.md).

## Windows 64 bits

Installez Git et Python 3.11 64 bits, puis utilisez PowerShell :

```powershell
git clone https://github.com/gaelcado/Song2Agostini.git
cd Song2Agostini
py -3.11 scripts/bootstrap.py --desktop
```

Installez également FFmpeg et MuseScore depuis leurs distributions officielles. Assurez-vous que leurs exécutables sont accessibles ; [le guide technique](docs/installation-technique.md) explique les chemins et les diagnostics.

```powershell
py -3.11 scripts/bootstrap.py --check --desktop
.\work\envs\app\Scripts\drum-lab-desktop.exe
```

La fenêtre est intégrée à l’application : elle n’ouvre pas votre navigateur. Windows 10 et 11 sont les cibles prévues, mais ne sont pas encore certifiés par des tests sur ces deux versions. WSL est un parcours séparé et ne valide pas l’exécutable Windows.

## Utiliser

Choisissez votre audio, cliquez sur « Générer la partition », puis consultez le PDF et téléchargez les formats souhaités. Relisez les avertissements rythmiques et faites vérifier le brouillon avant de le donner à un élève.

Si le contrôle d’installation échoue, conservez son message et demandez à votre agent de le résoudre. Les environnements du projet sont isolés : ne modifiez pas Python global pour corriger une dépendance.
