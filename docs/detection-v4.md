# Audit détection et phase v4 — 10 octobre 2026

Travail recherche audio uniquement : aucun accès aux feuilles manuelles, manifests
privés, candidates ou erreurs détaillées du vérificateur. Les retours employés sont
agrégés : confusion grosse caisse/caisse claire et premiers temps souvent attribués
à la caisse claire. Aucun instrument n'est imposé sur le premier temps.

## Chaîne des classes vérifiée

Le package ADTOF-pytorch installé déclare `LABELS_5 = [35, 38, 47, 42, 49]`.
Le peak picker parcourt les colonnes dans cet ordre et conserve ces numéros MIDI.
Les seuils `[.22,.24,.32,.22,.30]` sont donc, dans l'ordre : grosse caisse,
caisse claire, toms, charleston, cymbales. Attention : cet ordre n'est pas l'ordre
alphabétique ni « kick/snare/hi-hat/toms/cymbals ».

| Colonne | MIDI brut | Classe JSON | Position exportée |
|---|---:|---|---|
| 0 | 35 | kick | fa4, tête normale |
| 1 | 38 | snare | do5, tête normale |
| 2 | 47 | toms | ré5, tête normale |
| 3 | 42 | hi-hat | sol5, croix |
| 4 | 49 | cymbals | la5, croix |

Le worker, la validation `drum_only_events`, le MIDI et `KIT` sont cohérents.
MusicXML utilise `midi-unpitched = pitch+1`, convention à base 1 correcte.
Aucune inversion globale kick/snare prouvée. Les classes ADTOF sont des familles :
le pitch 49 n'établit pas que chaque cymbale détectée est acoustiquement un crash,
ni 47 que chaque tom est réellement médium. Les détections ne produisent pas
les distinctions fines du kit. La légende d'export demeure nécessaire.

## Bug logiciel certain corrigé

`quantization.py` extrapolait avant le premier beat avec la totalité du premier
intervalle, même si cet intervalle contenait plusieurs beats manquants dans un
silence. Une anacrouse pouvait alors être déplacée vers une mauvaise subdivision.
Après le dernier beat, le tempo médian était utilisé au lieu de l'intervalle local.
Les deux bords utilisent maintenant l'intervalle local divisé par le nombre de
beats manquants déjà estimé. Le placement dans la mesure et les classes ne sont
pas changés arbitrairement. Grilles non finies, tempo nul et liste vide sont rejetés.

Validation : `.venv/bin/python -m pytest tests/test_quantization.py
 tests/test_pipeline.py tests/test_engraving.py -q` : 36 tests passent.
Fixtures synthétiques, pas benchmark musical.

## Phase des mesures : essai audio indépendant

La grille Librosa existante traite la première pulsation suivie comme premier
temps et divise les tempos supérieurs à 160 BPM. Ce sont des hypothèses déclarées,
pas une inférence des mesures. Un premier temps portant la caisse claire ne prouve
pas une erreur : l'instrument n'identifie pas à lui seul la phase.

L'essai expérimental `configs/phase-beat-this-v4.json` emploie Beat This! final0
sur le mix complet, CPU, sans DBN, avec les mêmes événements ADTOF sur batterie
isolée et les mêmes seuils. Le défaut produit reste `grid_engine=librosa`.
Le code et les poids sont MIT selon les auteurs ; CPU est officiellement pris
en charge. [Dépôt officiel Beat This!](https://github.com/CPJKU/beat_this).

- Commit : `b95c8ab0c58c2d9fcfd40508ae8dffbc05ac4f5c`.
- Poids final0 (~81 Mo décimaux) : SHA256
  `8c328b45f59d8dd3dff219253ff6a8d6482be57d0133a29140e2febbf8eb8331`.
- Environnement isolé : `work/envs/beat_this`, dépendances figées dans
  `configs/beat-this.lock.txt`, modèle dans `configs/beat-this-model.json`.
- Commande : `.venv/bin/python -m drum_lab.cli run data/raw/audio/piece_01.mp3
  configs/phase-beat-this-v4.json --piece piece_01`.
- Run figé : `20261010T102742-6af05201`, chaîne complète 10,30 s, estimation de
  grille 3,75 s CPU, 1 162 événements. PDF, MusicXML, MIDI brut et quantifié prêts.
- Origine proposée : 0,92 s ; tempo médian 90,91 BPM. La fraction d'intervalles
  entre downbeats comportant exactement quatre beats suivis est 0,7683.
  Ce résultat doit rester brouillon : le modèle n'impose pas une phase 4/4 uniforme.
- Activation downbeat médiane : 0,9954. Elle est non calibrée et ne constitue
  ni confiance musicale validée ni mesure de fidélité.
- Diagnostic audio RMS indépendant : activité 0,279 à 209,258 s ; aucun downbeat
  prédit avant cette activité. L'origine plus précoce que celle de Librosa ne
  démontre donc pas une génération de beats dans le silence initial.

| Diagnostic de quantification | Run antérieur 092826 | Essai phase 102742 |
|---|---:|---:|
| Déplacement médian | 40,32 ms | 19,55 ms |
| Déplacements >50 ms | 200 | 21 |
| Collisions même instrument | 15 | 10 |
| Mesures après export | 78 | 88 |

Ces diagnostics concernent le placement des coups déjà détectés. Ils ne prouvent
aucune amélioration du nombre de coups corrects ni du premier temps. Vérification
indépendante de la sortie figée demandée à l'orchestrateur. Aucun essai piece_02.

## Comparateurs locaux examinés

| Outil / source primaire | Code et poids | Faisabilité et décision |
|---|---|---|
| [ADTOF Plus](https://github.com/xavriley/adtof_plus_drum_transcription) et [MDX23C](https://github.com/xavriley/mdx23c-drum-separation) | Wrapper MIT ; ADTOF conserve CC BY-NC-SA 4.0. La licence du wrapper ne couvre pas automatiquement les poids de séparation tiers. | Pipeline mix→kit→éléments→ADTOF, pertinent pour confusions kick/snare. Ne pas lancer le téléchargement automatique tant que provenance, hash et licence du checkpoint exact ne sont pas établis. |
| [Timbrica](https://huggingface.co/Faridzar/timbrica-drum-separator) | Carte des poids CC BY-NC-SA 4.0 ; trois ONNX, ~19,7 Mo chacun ; code de traitement à implémenter et versionner localement. | I/O explicite STFT stéréo 4096/hop1024, masque kick/snare/toms. Meilleur second essai borné : séparation batterie puis ADTOF par branche. La séparation n'est pas elle-même un nouveau transcripteur. Autre agent prépare l'adaptateur et le smoke, coordonné avec root. |
| [inagoy DrumSep](https://github.com/inagoy/drumsep), [conversion Splitzo](https://huggingface.co/splitzo/drumsep) | Code original MIT ; conversion déclare MIT pour son modèle. Source originale ne distingue pas explicitement une licence spécifique des poids. | 4 stems, cymbales incluant charleston, ONNX ~335 Mo et segments 40 s : viable CPU en principe, coût mémoire plus élevé. Pas prioritaire face au candidat Timbrica documentant précisément son I/O. |
| [Omnizart](https://github.com/Music-and-Culture-Technology-Lab/omnizart) | Code MIT ; licence distincte checkpoints non établie dans le README consulté. | Les auteurs annoncent incompatibilité Mac ARM et bugs d'entraînement drum. Ce Mac est arm64. Écarté pour les deux essais actuels ; pas supposé interchangeable sans validation. |
| [ADT_STR](https://github.com/pier-maker92/ADT_STR), [HF](https://huggingface.co/Pierfrancesco/adt-str) | Dépôt CC BY-SA 4.0 ; carte HF sans licence explicitement affichée pour les poids. Ne pas déduire la licence des poids du seul code. | 26 classes, ~69 M paramètres, segments 2,56 s à 24 kHz, sorties onset/pitch/velocity. Candidat indépendant prometteur ; intégration et TorchCodec à vérifier CPU/Mac, téléchargement checkpoint et licence exacts à figer avant essai supplémentaire. |
| [Separate-and-Detect](https://github.com/ddman1101/Separate-and-detect), [HF auteur](https://huggingface.co/ddman1101/Separate-and-Detect) | Checkpoint auteur MIT ; dépendances VAE/vocodeur supplémentaires à auditer indépendamment. | Cinq stems et onset detector, diffusion latente, environnement madmom ancien et chemins inference orientés CUDA. Pas d'engagement raisonnable CPU court établi ; ne pas prioriser sur ce Mac. |
| [Wav2Vec2 drum-kit](https://huggingface.co/airasoul/wav2vec2-base-drum-kit) | Carte modèle MIT ; réutilise un modèle de base, audit licence dépendances nécessaire. | Classe un seul son court parmi dix classes ; ne transcrit pas la polyphonie. Ne pas appliquer argmax à un coup kick+snare simultané. Éventuel diagnostic après séparation, pas remplaçant direct ADTOF. |

Budget : un essai phase effectué ; un essai kit ciblé prévu par l'autre agent.
Aucun balayage de seuils, paiement, upload audio ou publication. Arrêter après ces
deux comparaisons jusqu'au retour indépendant agrégé ; les gains publiés par les
auteurs restent des résultats externes et ne sont pas des mesures de ces morceaux.
