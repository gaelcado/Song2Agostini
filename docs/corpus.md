# Dix compositions avec mixes multi-instruments et références originales

**Dix paires audio–MIDI sont effectivement acquises**, sous les identifiants `bench_01` à `bench_10`. Elles répondent à la priorité donnée aux morceaux avec plusieurs instruments. Ce sont des œuvres publiées par leurs auteurs sur OpenGameArt, en version complète telle que mise à disposition ; plusieurs sont des compositions courtes ou des musiques de jeu bouclables. Aucun extrait audio ni morceau reconstruit localement n’a remplacé l’audio publié. Les versions « loop » ou « Guitar » distinctes ont été évitées quand la page proposait aussi la version principale.

Les dix références sont des **MIDI originaux de composition**, pas des transcriptions produites par nos moteurs ni des partitions copiées des feuilles de l’apprenant. Un fichier MuseScore source supplémentaire est conservé pour `bench_08`. Les dix MIDI contiennent à la fois une percussion sur le canal standard de batterie et des notes sur des canaux mélodiques. Ce contrôle structurel ne certifie pas l’exhaustivité, le mapping, la conformité au rendu audio ni l’alignement. Tous restent `human_validated=false` et `evaluation_ready=false`.

## Sources, licences et attribution

Chaque page officielle de dépôt par l’auteur indique **CC0**, avec audio et source MIDI joints sur cette même page. Les liens ci-dessous constituent les sources primaires, et leurs copies HTML horodatées/empreintes restent côté vérification. Les fichiers MIDI, audios et fichiers source ont leurs URL exactes et SHA-256 dans la configuration d’import et le manifeste privé. La [déclaration CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) facilite la réutilisation sans obligation d’attribution ; nous créditons néanmoins tous les auteurs. Il s’agit de la licence déclarée par ces créateurs, pas d’un audit juridique de chaque instrument virtuel ou banque de sons. Aucune licence de code n’a été confondue avec celle des œuvres.

| Cas | Œuvre et source primaire | Auteur | Durée audio (s) | Licence |
|---|---|---|---:|---|
| bench_01 | [Boss Battle 10 [Retro]](https://opengameart.org/content/boss-battle-10-retro) | nene | 33.926 | CC0 1.0 |
| bench_02 | [Fight for Better Future [Rock/Metal]](https://opengameart.org/content/fight-for-better-future-rockmetal) | nene | 68.129 | CC0 1.0 |
| bench_03 | [Rock Music](https://opengameart.org/content/rock-music-0) | Umplix | 38.647 | CC0 1.0 |
| bench_04 | [Rock Theme 3](https://opengameart.org/content/rock-theme-3) | Umplix | 69.120 | CC0 1.0 |
| bench_05 | [C64 Style 3](https://opengameart.org/content/midi-pack-1-24-new-tunes) | Tozan | 151.294 | CC0 1.0 |
| bench_06 | [Piano Blues with Drums Style 1](https://opengameart.org/content/midi-pack-1-24-new-tunes) | Tozan | 116.045 | CC0 1.0 |
| bench_07 | [Pirate 5](https://opengameart.org/content/midi-pack-1-24-new-tunes) | Tozan | 162.924 | CC0 1.0 |
| bench_08 | [Prepare your swords](https://opengameart.org/content/prepare-your-swords) | Bojidar Marinov (bojidar-bg) | 88.346 | CC0 1.0 |
| bench_09 | [Rewind](https://opengameart.org/content/rewind) | Alex McCulloch (Pro Sensory) | 117.786 | CC0 1.0 |
| bench_10 | [Long Away Home [8bit]](https://opengameart.org/content/long-away-home-8bit) | nene | 121.327 | CC0 1.0 |

Total : **16.13 minutes**, cinq auteurs ; **76,856,904 octets** pour les vingt fichiers audio/MIDI sélectionnés, hors copies des pages et source MuseScore additionnelle.

## Intégrité, import et formats

Commande reproductible depuis la racine :

```sh
.venv/bin/python lab/scripts/import_benchmark.py --config configs/corpus-oga-v1.json
```

La configuration épingle les URL et empreintes de chaque original. Le script réutilise les originaux conservés, contrôle leur SHA-256, refuse d’écraser un original de contenu différent, puis contrôle la présence de percussion et de mélodie dans le MIDI. `mido` est utilisé depuis l’environnement isolé du projet ; Python global n’est pas modifié. `ffprobe` relève les métadonnées audio. Les originaux WAV/MP3 sont copiés sans modification. Pour `bench_05`, `bench_06` et `bench_07`, l’OGG publié reste conservé et une conversion explicitement dérivée en WAV PCM16 fournit le format pris en charge par les moteurs ; le script appelle `ffmpeg`, sans fabriquer un nouveau rendu musical à partir du MIDI.

Contrôles terminés : vingt fichiers présents, empreintes originales conformes, dix WAV/MP3 décodables, dix MIDI lisibles avec percussion et mélodie, dix références non validées explicitement marquées, manifeste recherche sans chemin MIDI/score ni métadonnée d’alignement. La réexécution depuis les originaux en cache a réussi. L’audit indépendant de correspondance audio–partition reste nécessaire : un compositeur peut exporter un MIDI dont les sons, durées ou articulations diffèrent du master publié.

## Séparation et diversité réelle

Le manifeste `data/benchmark-research-manifest.json` expose les dix audios, leurs empreintes et métadonnées audio, titres, auteurs, source/licence et descriptions générales. Il ne fournit ni MIDI, note attendue, grille, mapping ni alignement. `data/benchmark-manifest.json` conserve les références et la provenance complète pour le vérificateur. Les fichiers source sont sous `data/raw/audio/corpus-sources/` et `data/raw/scores/corpus-sources/` ; les copies normalisées sont `data/raw/audio/bench_XX.*` et `data/raw/scores/bench_XX.original.mid`. Ces originaux/intermédiaires restent hors Git. La séparation demeure logique dans le système de fichiers partagé, conformément à `docs/separation.md`.

La sélection donne plusieurs auteurs et des sonorités/styles déclarés différents : rock/metal, rétro aventure, musique de jeu C64/pirate, piano blues, jazz/chiptune et fantasy/ambient. Les morceaux sont synthétisés ; ils ne constituent pas dix sessions acoustiques enregistrées. Aucun changement de signature, swing mesuré, fill, silence ou niveau de difficulté spécifique n’est revendiqué pour le corpus principal avant audit indépendant. Les descriptions des œuvres sont celles des auteurs. La grille issue du MIDI et les différences détaillées ne doivent pas être transmises à la recherche. Le futur PDF/MusicXML de référence doit rester réservé à la vérification et clairement marqué comme rendu de source.

Les morceaux `piece_01`/`piece_02`, leurs partitions et leurs prédictions n’ont pas été consultés pendant cette acquisition. Aucun moteur, réentraînement, upload audio ou score musical n’a été exécuté. Le corpus principal est un corpus de développement candidat tant que protocole et validation ne sont pas figés ; dix morceaux publics ne prouvent pas la généralisation ni l’absence de recouvrement avec des jeux d’entraînement.

Un premier candidat `Caverns 1` a été retiré du corpus principal après échec du contrôle indépendant de correspondance audio–MIDI, et remplacé par `C64 Style 3`. Ses originaux et preuves de provenance restent conservés hors sélection. Le remplacement a passé le contrôle de qualification structurelle indépendant ; aucune validation humaine ni alignement fin n’est déduit de ce contrôle.

Pistes écartées : Slakh/BabySlakh, faute de preuve suffisante ici des droits des compositions issues de Lakh ; les six titres Roppy Chop, dont l’export MIDI téléchargé ne fournit pas de batterie sur le canal standard ; Menu Loop, dont les pistes nommées « drums » ne suffisent pas à établir un mapping percussion fiable. Ces exclusions sont des décisions d’acquisition conservatrices, pas des jugements sur la qualité de ces musiques. Leurs fichiers candidats ne sont pas présentés comme références évaluables.

## Corpus de percussion complémentaire

Les dix cas `tech_01` à `tech_10` ci-dessous sont conservés pour les cas techniques de batterie seule. **Ils ne comptent pas parmi les dix morceaux principaux**. Leurs manifestes sont distincts : `data/benchmark-percussion-manifest.json` (vérification) et `data/benchmark-percussion-research-manifest.json` (audio uniquement).

---

### Groove MIDI Dataset v1.0.0

Corpus technique complémentaire : il ne compte pas parmi les dix morceaux complets demandés.

Dix paires ont été importées le 10 octobre 2026 depuis la [source officielle Google/Magenta](https://magenta.withgoogle.com/datasets/groove). Ce sont neuf performances et un fill court de batterie électronique joué par des humains, avec l’audio synthétisé enregistré par la source et son MIDI original. Il ne s’agit pas de dix chansons complètes, de mixes multi-instruments, ni d’enregistrements de batterie acoustique. Aucun moteur de transcription n’a produit les références.

## Licence et attribution

La page officielle et le fichier `groove/LICENSE` inclus dans l’archive MIDI déclarent **Creative Commons Attribution 4.0 International** pour le dataset. Cette autorisation porte sur les données audio/MIDI, pas seulement un dépôt de code. La [licence CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) autorise la réutilisation et l’adaptation avec attribution, lien vers la licence et indication des modifications. Les originaux importés sont copiés sans modification ; leur renommage local ne change pas leur contenu. « Libre » ne signifie pas domaine public ou absence de toute obligation.

Attribution : **Google LLC — Groove MIDI Dataset v1.0.0**. Jon Gillick, Adam Roberts, Jesse Engel, Douglas Eck et David Bamman, *Learning to Groove with Inverse Sequence Transformations*, ICML 2019. Les interprètes sont crédités dans les remerciements de la page officielle ; les identifiants anonymisés d’origine sont conservés côté vérification.

## Sélection et limites

La sélection est déterministe dans `configs/corpus-gmd-v1.json`. Les genres et descriptions sont les étiquettes fournies par la source, pas une validation musicologique locale. Elle varie styles, interprètes, tempi, durée et métriques déclarées, notamment swing/shuffle et métriques inhabituelles. Aucun degré de difficulté, roulement ou silence précis n’est revendiqué sans audit. Les dynamiques et la richesse instrumentale n’ont pas été inspectées pour fabriquer une prédiction. La grille musicale et les événements restent exclusivement du côté vérification ; l’étiquetage source ne doit pas servir de grille à la recherche.

Le corpus ne prouve pas la robustesse sur des chansons réelles ni la généralisation. Son éventuel recouvrement avec les données d’entraînement de certains moteurs doit être audité : ce corpus public ne constitue pas automatiquement un test inédit. Les partitions acceptées ici sont dix MIDI originaux du dataset. Il ne contient pas dix PDF pédagogiques préexistants. Un rendu futur PDF/MusicXML des références doit être marqué comme dérivé de la référence et rester réservé au vérificateur.

Slakh/BabySlakh a été examiné comme piste de mixes synthétiques, mais n’a pas été importé : sa provenance Lakh MIDI et la licence affichée du dataset ne suffisent pas ici à établir les droits des compositions originales. Aucun audio n’a été envoyé vers un service extérieur.

## Import et intégrité

Commande depuis la racine du projet :

```sh
python3 scripts/import_benchmark.py --config configs/corpus-gmd-v1.json
```

Le script utilise uniquement la bibliothèque standard Python, sans modifier Python global. Il vérifie le SHA-256 de l’archive MIDI, la mention de licence, les CRC ZIP, puis enregistre les SHA-256 des fichiers originaux. L’archive audio officielle est épinglée par version, taille et génération Google Storage. L’import HTTP Range ne télécharge que le répertoire ZIP et les membres sélectionnés, avec un plafond explicite de 2,5 Go. Le SHA-256 de l’archive audio entière publié par la source est conservé à titre de provenance ; **il n’a pas été vérifié**, puisque l’archive entière n’est pas téléchargée. Aucun original existant de contenu différent n’est écrasé.

Transfert effectif de cet import : **167,295,237 octets** ; durée audio totale : **21.84 minutes**. Vérification locale : dix fichiers WAV lisibles, dix en-têtes MIDI valides, empreintes audio/MIDI conformes, dix flags `human_validated=false` et `evaluation_ready=false`. Ces contrôles d’intégrité ne valident pas les notes ni leur alignement.

## Séparation

`data/benchmark-percussion-research-manifest.json` expose uniquement les chemins audio, empreintes audio, durée et format, licence/source et descriptions de cas. Il ne contient ni chemin MIDI ni événement, mapping, tempo musical explicite ou alignement de référence. `data/benchmark-percussion-manifest.json` conserve les dix liens audio–MIDI, les empreintes MIDI et les métadonnées de référence ; il est réservé à la vérification suivant `docs/separation.md`. Les originaux se trouvent sous `data/raw/audio/` et `data/raw/scores/`, hors Git.

La source annonce un alignement audio/MIDI très précis, mais cet import ne le valide pas indépendamment. Avant toute mesure : auditer le mapping propre à Roland, la couverture, les contrôles du charleston et la politique d’alignement, puis geler cette politique sans consulter les prédictions. Aucune validation humaine n’est inventée. La séparation est logique dans le système de fichiers partagé.

## Inventaire audio public

| Cas | Description source | Durée audio (s) | SHA-256 audio |
|---|---|---:|---|
| tech_01 | Rock progressif ; métrique inhabituelle déclarée par la source | 141.818 | `43ae4c0c0ad7e419e01c6198c4f2443fbd49eaf23a994df08cf4b41241a63cf7` |
| tech_02 | Merengue vénézuélien ; métrique inhabituelle déclarée par la source | 167.593 | `98b8c8e83eaa73b518949acd179cee85d3fb0c39e4ba044bb671ea0dabfcd4c3` |
| tech_03 | Rock lent ; métrique composée déclarée par la source | 77.780 | `07c728e020219c9f8a415cf2dd94786db2cd3a8ad2d03f5cf3e14efe72b3a4cb` |
| tech_04 | Chacarera ; métrique ternaire déclarée par la source | 149.061 | `e755ee22fae0fb31b2043ca227331a1774eeb7248c47f07ee5ab94dbbea480d5` |
| tech_05 | Jazz swing, étiquette fournie par le batteur | 176.677 | `24a83d9131caed2adb9c8bed048cef90ca4ae04a05a421a64917a416de3d74a0` |
| tech_06 | Funk Purdie shuffle, étiquette fournie par le batteur | 193.830 | `e285cb27c9a11cc4ef38753673256185ac19afc9a9c21508794b7ab69001c434` |
| tech_07 | Reggae lent, étiquette fournie par le batteur | 112.500 | `c336210485cf54044a8e536ab2fdc57dbc3c6e7a4b448006669ddbd4e82b7889` |
| tech_08 | Punk rapide, étiquette fournie par le batteur | 203.333 | `fd1cb12fe493554781c1e3c96c79cf48ec959c7e0a10d914ba73d1b140597de4` |
| tech_09 | Hip-hop, autre interprète | 84.000 | `8c869296d6219a2723bb967c0e94dc31b68177be6ebd0d9c7e7fd4c01d7711c6` |
| tech_10 | Fill court ; cas limite de durée, étiquette source | 3.692 | `0d359de855c1087a4cfb2c1e9174dd4db7c1347cfe04adceb7b2214451e4f721` |
