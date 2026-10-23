# Développement sur server-cado

Le dossier de travail principal est désormais
`/home/gaelcado/projects/christophe-avon` sur `server-cado`.
Le checkout du Mac est conservé, avec ses originaux et ses environnements macOS.
Faire les prochains commits depuis le serveur ; récupérer ensuite les changements
avec Git sur le Mac avant d'y reprendre du travail.
L'identité de commit est configurée dans le dépôt serveur. L'authentification
GitHub du Mac n'est pas copiée : le serveur peut lire le dépôt public, mais
nécessite sa propre connexion GitHub pour pousser les prochains commits.

```sh
ssh server-cado
cd ~/projects/christophe-avon
.venv/bin/python -m pytest -q
bash scripts/dev-server-cado.sh serve --port 8765
```

Depuis un autre terminal du Mac :

```sh
ssh -N -L 8765:127.0.0.1:8765 server-cado
```

Ouvrir ensuite `http://127.0.0.1:8765`. Le serveur de l'application écoute
uniquement sur la boucle locale. Le script utilise directement `src/` : les
modifications Python et web sont prises en compte au prochain lancement.

## Runtime et fichiers privés

Python 3.11 est installé pour cet utilisateur, sans modification du Python
système. Les environnements Linux sont sous `work/linux-runtime/envs/` ;
`.venv` pointe vers l'environnement app. Le runtime Linux est distinct des
preuves d'installation historiques copiées depuis le Mac.

Les données, références, sorties, caches et médias du site ont été transférés
directement par SSH, hors Git. Les poids existants sont réutilisés ; aucun audio
n'est envoyé à un service de transcription. `public/audio/`, `public/images/`,
`files/` et `storage/` du site restent privés. Un clone public seul n'a donc pas
les médias nécessaires pour reproduire le site complet.

Les environnements macOS, bundles `dist/`, applications `.app` et images `.dmg`
ne sont pas copiés sur Linux. Les anciens rapports peuvent conserver des chemins
absolus du Mac comme provenance ; ils ne sont pas réécrits. Les liens symboliques
absolus internes au projet sont adaptés dans la copie serveur seulement.

Diagnostic du runtime :

```sh
.venv/bin/python scripts/bootstrap.py --check --runtime-root work/linux-runtime
```

Le diagnostic doit rester en échec tant que FFmpeg, FFprobe ou MuseScore manquent.
La suite logicielle ne valide pas une transcription musicale ni un rendu PDF
natif Linux. Aucune nouvelle boucle musicale n'est exécutée pendant ce transfert.

## Site Christophe Arent

Node 24 est déjà disponible sur le serveur. Les dépendances sont reconstruites
avec `npm ci` ; `npm run build` génère les pages. Le serveur de vente n'est pas
lancé en permanence et aucun webhook Stripe n'est activé pendant la migration.

```sh
cd ~/projects/christophe-avon/site-christophe-arent
npm ci
npm run build
```
