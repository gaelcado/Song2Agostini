## Développement transféré sur server-cado — 23 octobre 2026

Code en cours sauvegardé dans `60b8405` et poussé sur `origin/main`, avec les sources du site Christophe Arent. Audios, photos, références, SQLite, modèles et résultats restent hors Git. Copie privée SSH de 2 959 235 104 octets vers `/home/gaelcado/projects/christophe-avon`, originaux Mac conservés ; contrôle rsync par sommes de contrôle sans écart de contenu privé. Cinq liens absolus internes adaptés côté serveur, cibles d'origine journalisées ; rapports historiques non réécrits. SQLite `quick_check` réussi.

Ubuntu x86_64, Python 3.11.17 utilisateur, quatre environnements Linux isolés : app, ADTOF, Demucs et Beat This. Imports et cohérence des dépendances réussis, trois poids existants vérifiés par SHA-256. Runtime distinct `work/linux-runtime/` ; aucun nouveau téléchargement de modèle ni transcription. 258 tests logiciels réussis sur le Mac (Python 3.11.14) et sur le serveur (9,40 s au contrôle final). Interface HTTP locale : 200 ; site Node 24 : `npm ci`, construction et syntaxe JavaScript réussies. Preuves serveur : `work/migration-server-cado/`, `.migration-tools/` et `work/linux-runtime/runtime-install.json`.

Limites : FFmpeg, FFprobe et MuseScore absents, donc `ready: false`, chaîne audio→PDF Linux non testée. Fenêtre desktop Linux et fidélité musicale non évaluées pendant ce transfert. Authentification GitHub propre au serveur encore à configurer pour les futurs push ; identité de commit configurée, lecture publique vérifiée. Les commits de migration sont poussés depuis le Mac. Reprise et tunnel SSH : [developpement-server-cado.md](developpement-server-cado.md).

## Boucle de vérification automatique — 17 octobre 2026

Le retour musicien hebdomadaire est complété par un vérificateur automatique (`docs/boucle-automatique.md`) : références réelles saisies par l'agent (Perfect Strangers, Deluxe Michael, Crazy, Heathens ; non validées humainement), MIDI GMD tech_01–09 et OGA bench_02/08. Métrique principale : note écrite dans la bonne mesure, au bon temps, sur le bon instrument (MusicXML expansé). L'utilisateur a demandé un travail sans sous-agents : séparation recherche/vérification seulement logique, réglages sur moyennes.

Défaut principal trouvé : mesures comptées depuis la première pulsation (intro comprise), d'où une partition entière décalée d'un temps sur Perfect Strangers et aucun 5/4 possible. Correctif : mesures de longueur variable choisies par programmation dynamique sur l'activation des premiers temps Beat This, longueur dominante apprise du morceau, indices de kit ; gravure MusicXML avec changements de signature. Mesure+temps réels 0,607 → 0,822, GMD 0,550 → 0,751 ; mesures exactes réels 75 % → 97,5 %. Contrôle gelé Bacalao con pan (jamais utilisé pour régler, saisi après le gel) : 0,310 → 0,689, mesures exactes 41/88 → 81/88. Détection inchangée. Activé dans le produit (`PRODUCT_CONFIG`) avec cymbales régulières écrites en ride. 258 tests passent. Bundle macOS non reconstruit.

Prochaines actions : charleston manqué sur contretemps (sélection absolue en réserve), caisse claire et cymbales de Bacalao, signification des « (x) » de Crazy à demander au batteur, swing/triolets.

## Lecteur PDF du bundle corrigé — 10 octobre 2026

Le panneau gris est reproduit avec les restrictions réelles de la fenêtre native : l’intercepteur bloquait les modules internes `chrome://resources/` importés par le lecteur PDF Chromium. Le test visuel précédent utilisait un profil sans cet intercepteur et ne couvrait donc pas ce défaut. Correction `854e3a2` : autorisation de cet hôte interne précis, sans autoriser les autres hôtes ni les requêtes réseau externes. 29 tests ciblés passent, dont les régressions sur la politique de ressources.

Bundle `dist/Song2Agostini.app` reconstruit, signature profonde stricte vérifiée, source desktop embarquée identique. Vérification réelle via l’interface native du binaire : sélection de `piece_02.mp3`, génération terminée (`d161f3f60e3547f2a3e9b0d19cb7f34f`), PDF de quatre pages visible, défilement dans le lecteur de la page 1 à la page 2 et défilement extérieur de la fenêtre réussis sans cliquer les barres. Application laissée ouverte. Logs de reproduction et capture locale : `work/pdf-viewer-debug/`. L’ancienne DMG reste inchangée ; ouvrir le bundle corrigé.

## Application reconstruite et lancée — 10 octobre 2026

Bundle natif macOS Apple Silicon reconstruit depuis `cfdb979` avec le runtime local complet : `dist/Song2Agostini.app`. Commande : `.venv/bin/python packaging/build_desktop.py --runtime-payload work/desktop-runtime`. Signature vérifiée avec `codesign --verify --deep --strict` ; JavaScript embarqué identique aux sources.

Test réel du binaire figé depuis `/tmp`, PATH système, variables Python/runtime héritées retirées et répertoire de travail applicatif neuf : génération audio seule de `piece_01.mp3` réussie en 107,71 s. PDF, MusicXML, MIDI brut et MIDI quantifié présents, empreintes vérifiées. Preuves privées : `work/desktop-smoke/pdf-first-cfdb979/desktop-smoke.json`, capture de fenêtre et logs ; métadonnées dans `dist/Song2Agostini-build.json`. Lancement normal effectué avec `open -n` sur ce bundle. Cette vérification porte sur le fonctionnement macOS, pas sur la fidélité musicale. L’ancienne image DMG n’a pas été reconstruite ; utiliser le bundle `.app` indiqué.

## Écran final centré sur le PDF — 10 octobre 2026

Le résultat affiche le PDF complet dans un lecteur intégré avec navigation multipage, puis conserve les formats supplémentaires et diagnostics dans des volets repliés. Deux actions principales : téléchargement PDF et ouverture du MusicXML éditable dans MuseScore. Le lancement préfère MuseScore 4, puis 3 selon les installations locales ; message explicite et téléchargement MusicXML en repli si aucun éditeur n’est trouvé.

L’action d’ouverture est un POST local authentifié, réservé au traitement terminé de la session et à son fichier MusicXML interne ; aucun chemin fourni par le navigateur ni commande shell. Tests des accès intersessions, CSRF, fichier hors résultat et éditeur absent. Détection macOS/Windows/Linux testée de façon simulée ; ouverture réelle de MuseScore 4 réussie sur ce Mac. Le lecteur PDF a été contrôlé visuellement dans Qt WebEngine avec une sortie synthétique. 238 tests réussis en 8,08 s. Preuves locales : `work/ui-pdf-first/`. Les binaires distribués antérieurs ne sont pas reconstruits par cette modification des sources.

## Transitoires et ambiguïtés charleston/cymbale — 10 octobre 2026

Nouvelle passe bornée : une variante T1 sur les cinq nouveaux audios, sans hausse du plafond d’essais. Diagnostic exploratoire user_01 puis même règle sur les autres cas ; tous ont déjà été consultés et restent du développement. Chronologie et critères figés avant génération dans `work/research/transient-attacks-20261010/preregistration.json`. La vérification utilise un protocole distinct, fixé avant réception des candidates, sur le mix original.

Le filtre optionnel conserve la baseline et examine les propositions du seuil charleston 0,16. Il exige un transitoire aigu distinct, s’abstient près d’une cymbale prédite et interdit de réutiliser un pic déjà attribué. Aucune complétion périodique, aucune reclassification. Les fichiers `detector-raw.mid` et `detector-events.json` sont préservés avec empreintes avant les ajouts. Source commise `53ceb8e`, détails `docs/transient-candidates.md`.

T1 retient 48 ajouts (3/17/15/6/7), contre 191 pour la baisse de seuil seule. Zéro retrait, autres classes inchangées ; copies du détecteur byte-identiques aux baselines sur les cinq cas. Contrôle indépendant du mix : 29/48 ajouts passent le seuil énergétique exploratoire préfixé de +6 dB, contre 1/46 instants décalés utilisés comme témoins descriptifs, non comme négatifs annotés. Résultats par cas : 3/3, 12/17, 11/15, 0/6, 3/7. Une hausse d’énergie peut venir d’un autre instrument ; ce résultat n’est ni une précision instrumentale ni une preuve de gain de fidélité. Les six ajouts de Toxicity ne sont pas corroborés par ce critère indépendant.

Cinq intégrités passées, 27 pages inspectées lisibles, erreur XML/MIDI maximale 1,274 ms. Les baselines courantes restent retenues, paramètres expérimentaux désactivés par défaut. Dix paires de caisse claire à 60–80 ms restent ambiguës ; six présentent deux transitoires distincts dans le diagnostic recherche, sans démontrer un fla plutôt qu’un autre geste. Aucun symbole de fla ajouté.

233 tests passent en 6,74 s ; génération des cinq runs 26,5 s et diagnostic 5,6 s, sans nouvelle inférence des modèles. Budget cumulé : user_01 8/13, autres 7/13. Arrêt après la variante prévue. Preuves privées : `work/research/transient-attacks-20261010/` et `work/verification/attaques-v2-20261010/`. Comparaison PDF/XML et six courts extraits pour écoute sont conservés dans ces dossiers. F1/complétude musicale restent N/A ; prochaine étape utile : confirmation instrumentale indépendante des candidats avant réglage ou adoption.

## Charlestons et triolets locaux — 10 octobre 2026

Boucle de développement bornée, audio seul, trois variantes sur chacun des cinq nouveaux audios : seuil charleston .22→.16 (canal 3 de LABELS_5), sélection de triolets locaux en mesure simple, puis combinaison. Pré-enregistrement, sources, commandes et quinze runs conservés sous `work/research/hats-tuplets-20261010/`. Activations et grille mises en cache, aucune nouvelle inférence des modèles ; 47,7 secondes cumulées de génération. Les cinq cas ont servi au développement, pas à un test indépendant.

Résultat : les variantes de seuil ajoutent 191 charlestons (+33/+80/+34/+33/+11), sans retrait ni changement d’une autre classe. Aucune amélioration de précision ou de complétude n’est démontrée. Le critère de triolets s’abstient sur tous les audios : V2 conserve événements, MIDI brut/quantifié et MusicXML identiques aux baselines ; V3 est identique à V1. Contrôle indépendant des quinze sorties passé : voix complètes, percussion et répétitions cohérentes, timing XML/MIDI ≤1,28 ms. Les rendus V2 et V3 sont pixel-identiques respectivement aux baselines et V1 ; les 27 pages V1 ont été inspectées. Les sorties courantes ne sont pas remplacées ; comparaison privée : `work/research/hats-tuplets-20261010/comparaison.html`.

Capacité logicielle ajoutée, optionnelle et désactivée par défaut : triolets locaux explicites en MusicXML avec résolution rationnelle, silences, accords, ligatures et reprises tenant compte de leur interprétation rythmique. Aucun coup n’est ajouté pour compléter un motif. Les groupes ordinaires du 12/8 restent distincts des triolets en mesure simple. Les tests synthétiques valident le logiciel, pas la qualité de détection dans un morceau. 222 tests passent en 7,06 s. Fixture synthétique réelle vérifiée indépendamment : trois mesures, quatorze attaques, six groupes de triolets lisibles, durées des deux voix correctes ; aller-retour MuseScore MIDI avec erreur maximale 0,758 ms. Ce résultat ne valide pas la détection musicale. Documentation : `docs/local-tuplets.md`.

Les flas restent non résolus : ADTOF travaille à 100 images/s avec suppression de pics voisins ; les dix paires de caisse claire rapprochées sur un audio sont ambiguës. Aucun symbole ni attaque secondaire fabriqués. F1, rappel et complétude musicale restent N/A faute de référence symbolique et d’alignement validés. Prochaine hypothèse à tester séparément : distinguer les attaques secondaires de caisse claire et les confusions charleston/cymbales à partir du signal audio, avant une nouvelle boucle préenregistrée. Rapports de vérification privés : `work/verification/hats-ornements-20261010/`.

## Signatures rythmiques — 10 octobre 2026

Le 4/4 historique était une limitation d'export, pas une signature inférée. Une méthode audio seule générique a été ajoutée au pipeline : cycles entre premiers temps Beat This et phases des pics de flux spectral sur le mix. Trois variantes bornées préenregistrées, sans règle par titre et sans lecture des références par la recherche. La variante v2 composée avec croches seules a été rejetée : collisions 1→44 et grands déplacements 2→239. La variante v3 conserve les doubles croches composées ; coups bruts et événements identiques à ceux des cinq anciens runs.

Candidates des cinq nouveaux audios : 4/4, 3/4, 4/4, 12/8, 4/4. La candidate composée reste une abstention sur le regroupement global/local, pas une phase validée. Pour Toxicity, déplacement médian 19,5→10,9 ms et maximal 60,5→59,1 ms, une collision conservée ; ce sont des diagnostics de quantification et non un score musical. Les quatre autres diagnostics sont inchangés. Les deux anciens audios ont été examinés après gel sans réglage : subdivisions ambiguës, abstention. Une seule inférence Beat This supplémentaire sur l'ancien audio sans cache, 5,94 s ; aucune nouvelle inférence des coups. Les deux passes de cinq exports ont réutilisé les caches, environ une minute de calcul cumulée.

Gravure réelle en signatures simples/composées : longueurs de mesures, durées, ligatures et unité de tempo cohérentes ; unité pointée affichée dans l'interface. Les changements locaux sont diagnostiqués mais ne sont pas exportés, et les alternatives de niveau de tempo restent ouvertes. Le cache est retraité depuis les pulsations observées, sans hériter d'une signature/tempo dérivés d'un traitement antérieur.

Contrôle indépendant : cinq intégrités passées, 27 pages lisibles (4/9/6/5/3), conversion XML/MIDI avec erreur maximale ≤1,28 ms après prise en compte de l'origine, références hors moteur. Comparaison documentaire agrégée : trois concordances globales, une partielle, une divergence majeure ; aucun nouveau réglage n'a suivi ce retour. Phase, placement contre référence et fidélité/F1 restent N/A. 216 tests logiciels passent en 6,50 s ; les huit tests métriques/affichage, dont le contrôle cache final, passent aussi. Les autres modifications préexistantes de l'interface sont préservées.

Preuves privées : `work/meter-audio-20261010/` (préenregistrement, profils, sources figées, rapports, variante rejetée, anciens audios), `work/verification/metres-2026-10-10/` (rapport et contrôle indépendant). `outputs/user_01` à `user_05` et l'index courant pointent vers les runs v3 ; anciens runs et index/associations historiques restent conservés. Méthode et limites : `docs/meter-audio.md`. Prochaine action musicale : résoudre les regroupements et changements locaux par une nouvelle recherche bornée, puis validation indépendante de phase/alignement ; ne pas considérer les chiffres de signature seuls comme une preuve de fidélité.

## Import Gmail et rangement — 10 octobre 2026

Cinq nouvelles paires audio/PDF identifiées dans les mails Part 1 à Part 5 : dix fichiers, pas dix nouveaux morceaux. Les cinq PDF originaux ont été téléchargés par le connecteur Gmail, avec tailles/signatures/SHA-256 contrôlés et onze pages inspectées par un vérificateur isolé. Les MP3 ont été fournis localement, le connecteur ne les prenant pas en charge.

Les six MP3 déposés à la racine ont été rangés sans changer leurs bytes sous `data/raw/audio/gmail-2026-10-10/`. Les feuilles restent sous `data/raw/scores/gmail-2026-10-10/`. L'utilisateur a remplacé l'entrée Crazy drumless par `Simple Plan - Crazy.mp3` ; ancien original et run failed conservés. `data/new-input-research-manifest.json` ne fournit que les entrées audio ; `data/new-input-validation-manifest.json` associe les cinq audios actifs aux feuilles et conserve l'historique. Ces manifestes et données restent hors Git.

Passe audio seule bornée : cinq cas initiaux, profil Demucs/ADTOF + grille Beat This figé, 583,87 s de calcul local. Quatre exports complets ; Crazy drumless zéro attaque et aucun PDF, run `20261010T120452-c92d106b`. Une seule reprise autorisée sur le fichier Crazy corrigé, même profil, 95,38 s, run `20261010T121508-c6e06f6e`. Aucun seuil ni note issus des références. Les snapshots exacts des scripts, manifestes et configurations sont conservés par passe. Rapport initial `work/new-inputs-20261010T120452/report.json`, remplacement `work/new-inputs-replacement-results.json`, résultats actifs `work/intake/gmail-2026-10-10/current-results.json`.

Les cinq audios actifs ont produit PDF/MusicXML/MIDI brut et quantifié/JSON. Contrôle isolé : Crazy quatre pages, Metallica sept, Scorpions six, Toxicity six et Heathens trois ; intégrité indépendante vérifiée, collisions déclarées conservées. Une consigne de reprise Scorpions débordait : nouvel export textuel sous le run `presentation-repair/`, musique inchangée, originaux conservés ; recontrôle indépendant réussi, texte entièrement dans la page et musique inchangée. Toutes les partitions restent des brouillons : phase, placement métrique et fidélité non validés. F1 N/A faute d'annotations symboliques et d'alignement humain validés ; lisibilité ne vaut pas fidélité.

Accès courant `outputs/user_01` à `user_05`, index `work/intake/gmail-2026-10-10/resultats.html`, association et audit détaillés privés sous `work/verification/gmail-2026-10-10/`. 207 tests logiciels passent en 8,00 s, `git diff --check` propre. Ces tests ne constituent pas un benchmark musical. Cinq brouillons lisibles, 26 pages contrôlées indépendamment. Prochaine action pour évaluer la fidélité : annotation et alignement indépendants validés humainement.

## Vérifications finales de distribution

198 tests logiciels réussis localement et sur les quatre runners (macOS 14, Ubuntu 22.04, Windows Server 2022/2025), commit 9c2f4d6, CI 38049467091. Une coupure TCP Windows lors du refus de POST a été corrigée : drainage des petits corps rejetés, borné à 64 KiB et 250 ms, refus 403/404 inchangés. Windows Server 2022 : export PDF natif MuseScore et forwards CPU ADTOF/Beat This/Demucs réussis ; validation d’entrée FFprobe N/A dans ce job. WSL1 Ubuntu 24.04 : 190 tests et validation audio/MIDI/XML/PDF réussis, artefacts récupérés. Windows 10/11 et WSL2 n’ont pas été testés. Preuves et URLs : docs/platform-support.md.

Les scripts des références et la vue privée sont sous lab/ ; la racine décrit uniquement le produit et l’installation. Le dépôt public ne contient ni musiques, ni références, ni poids, ni binaires tiers. Historique Git local ancien conservé sur master ; main public démarre d’un snapshot source audité. Installation neuve CPU PyTorch/torchaudio 2.11.0 distincte des workers privés gelés depuis les environnements historiques : aucune équivalence musicale inventée. Les caches identifient désormais leur runtime réel, et une grille historique sans identité n’est pas réutilisée avec un runtime installé nouveau.

MuseScore est copié physiquement avec sa signature officielle conservée. Sur Mac, la version 4.7.5 a encore interrompu des exports avec SIGABRT après restauration depuis l’image officielle ; une copie fraîche ne suffit donc pas à résoudre cette instabilité. La version 4.6.5 a réussi deux exports successifs puis le parcours complet de l’application figée : « Deluxe Michael » (217,94 s) → PDF/MusicXML/MIDI brut et quantifié en 55,39 s (sources finales 9c2f4d6), avec dossier utilisateur neuf sous /tmp, PATH système, modèles embarqués et aucune référence. Rapport privé : work/desktop-smoke/final-httpfix/desktop-smoke.json. Le test autonome Mac réel est suivi séparément dans docs/packaging.md ; les erreurs de construction et rendus sont conservées. Les droits de redistribution ADTOF-port et les notices complètes tiers bloquent encore une release publique de binaires complets. Fidélité musicale N/A ; aucun nouveau réglage ni accès aux feuilles manuelles pendant cette phase.

## Distribution — 10 octobre 2026

README/INSTALL/AGENTS/CLAUDE/STATUS à la racine simplifiés pour les musiciens et leurs agents. Scripts des références et ancienne vue déplacés sous lab/ ; les originaux et runs sont préservés. Licence MIT pour le code propre ; notices tiers distinctes. Publication limitée aux sources, aucun audio/référence/poids.

Installation neuve quatre environnements isolés, imports et pip-check réussis ; trois poids vérifiés par hashes. Qt desktop installé et fenêtre source/preview gelée lancées sur Mac. 179 tests logiciels passent. Smoke Mac MIDI→MusicXML→PDF réussi après un abort natif MuseScore documenté. Windows Server/WSL automatisés dans .github/workflows ; Windows 10/11 clients encore non testés. Construction complète privée en cours : redistribution publique bloquée par absence de licence explicite ADTOF-port, sans inventer une autorisation.

Preuves locales privées : work/release-smoke/runtime/runtime-install.json, work/platform-smoke-retry/report.json, work/desktop-smoke/. Les tests synthétiques et d’installation ne sont pas un benchmark musical. Fidélité musicale reste N/A.

# État — 10 octobre 2026

Projet : Song2Agostini. Dépôt public : https://github.com/gaelcado/Song2Agostini. Les originaux, références, environnements, poids, caches et sorties restent hors Git.

## Titres des morceaux — affichage produit

Les titres audio déposés « Deluxe Michael » et « Bacalao con pan » sont conservés
sur la projection audio seule. Le produit retrouve le titre par SHA-256 même
pour les copies nommées piece_01/piece_02 ; aucun titre n'est attribué par seul
identifiant ou nom de fichier. Pour un audio nouveau, le nom du fichier sert de
titre. Interface, entête PDF/MusicXML, nouveaux runs/CLI et noms de téléchargements
utilisent ce titre ; les identifiants historiques restent internes, les runs
figés inchangés. Le sous-agent contrôle association et séparation des références.
166 tests passent en 6,62 s. Vérification navigateur réelle : entrée et sortie
« Deluxe Michael », téléchargement `Deluxe Michael - partition.pdf`,
job `5fdac825586043aa8afe2b0eb1acbb02`, capture `work/product-titles.png`.
Sous-agent : trois pages inspectées, titre lisible, événements et MIDI identiques
à la précédente sortie, XML musical inchangé ; rapport `work/title-review.json`.
Deux premiers jobs ont échoué sur le SIGABRT natif MuseScore ; échecs conservés.
L’export PDF avec option `--no-audio` a réussi en CLI puis dans le produit,
sans annoncer pour autant une correction démontrée de tout crash natif.

## Gravure française et phase audio v5 — état courant

La sortie utilise désormais une convention française compatible Agostini :
grosse caisse sous la portée (D4 interne), caisse claire ligne centrale (B4),
cymbales voix haute, grosse caisse/caisse claire voix basse ; ligatures explicites
par temps. La légende décrit des emplacements, sans noms de notes de piano.
Les pitches GM, coups et tempos ne sont pas modifiés par cette présentation.
Sources pédagogiques et limites de MuseScore : `docs/notation.md`.

Le retour musicien sur la mesure huit visait la sortie historique de l'app,
qui choisissait sa première pulsation librosa comme début de mesure. Le produit
emploie maintenant explicitement Beat This! avec nettoyage des pics doublés,
indépendant des instruments et des références. Sur piece_01 : 26 pulsations
et cinq downbeats doublés retirés ; 77/77 intervalles downbeats de quatre temps.
La phase 4/4 reste une hypothèse, les changements de rythme restent limités.
Numérotation différente : les anciennes et nouvelles mesures huit ne désignent
pas le même instant audio. Détails : `docs/audio-grid-v5.md`.

Unique nouvel essai : `20261010T104109-a75f54de`, 6,89 s avec caches, sept essais
sur treize (six disponibles), aucun contrôle piece_02. Même MIDI brut et mêmes
1 162 événements ; 1 151 attaques gravées après 11 collisions déclarées.
Sous-agent isolé : trois pages lisibles, intégrité passée ; aucun snare sur le
premier slot des mesures contre 35 dans l'ancienne app. Snare sur pulsations
entières 1/2/3/4 : 0/50/0/50, avec 97 autres attaques sur subdivisions ;
depuis 29,65 s (ancienne mesure huit), 0/49/0/48. Feedback agrégé
`work/verification/agostini-v5/snare-phase-aggregate.json`. Ce diagnostic ne mesure
pas la fidélité. Référence et phase non validées humainement : F1 N/A.
Les métriques de déplacement >50 ms peuvent différer de deux coups selon
JSON/MIDI, du fait de l'arrondi temporel MIDI inférieur à 1 ms.

Parcours produit réel vérifié sans cache de grille fourni : job
`7a146108655c4d62984e37f595d6078f`, 6,48 s, aperçu chargé et téléchargements
PDF/MusicXML/MIDI réussis. Trois pages contrôlées indépendamment ; XML égal
au run v5 hors titre, MIDI identiques, hashes production exacts. Feedback
`output/agent-feedback.json` du job et preuves privées conservés. Une première
tentative de produit a échoué après trois SIGABRT MuseScore, puis une reprise
identique a réussi avec deux tentatives d'export. L'instabilité native reste
une limite, aucun remplacement par une ancienne partition. Capture
`work/product-agostini-v5.png`. 166 tests passent en 6,56 s.

La boucle s'arrête ici après le jugement final. Le moteur de détection reste
Demucs/ADTOF ; aucune substitution kick/snare, aucun coup imposé au premier
temps ni simplification pédagogique supplémentaire. Prochaine action musicale :
validation alignée dans le chat pour mesurer les erreurs locales restantes.

## Produit recentré et diagnostic de détection v4 — historique

Le handoff `docs/handoff-produit-et-simplification.md` définit le produit :
audio → génération → aperçu PDF et téléchargements. Navigation de validation,
routes `/verification`, assets associés et `/api/verification` retirés du
serveur, y compris pour les sessions locales valides. Les documents, décisions
et références historiques restent sur disque ; la vérification se déroule
dans le chat. 43 tests ciblés interface/store/pipeline passent à cette étape.

Retour musicien : confusion grosse caisse/caisse claire et caisse claire trop
souvent au premier temps. Audit du mapping : aucune inversion générale trouvée.
Lecture visuelle et analyse du signal par sous-agent isolé : hypothèse de phase
des mesures plausible, erreurs locales de détection encore possibles ; aucun
jugement humain ni écoute humaine inventés. Feedback privé filtré sous
`work/verification/musical-v4/feedback-public.json`, scores N/A.

Défaut confirmé : le premier beat suivi n'est pas une détection de premier
temps. Deux essais bornés terminés, sans promotion du moteur produit :

- Beat This! : run `20261010T102742-6af05201`, 10,30 s CPU, mêmes 1 162 coups bruts. Caisses claires exactement au début des mesures prédites : 35 → 2 ; grosses caisses : 17 → 39. Diagnostic sur les prédictions uniquement, pas fidélité. Intégrité passée, PDF trois pages accepté comme brouillon lisible ; origine et 4/4 restent provisoires.
- Timbrica kick/snare puis ADTOF : run `20261010T102825-8b369805`, 55,58 s CPU, 1 059 coups. Le sous-agent signale un possible filtrage excessif des grosses caisses ; phase inchangée. PDF figé quatre pages rejeté pour page orpheline. Nouvelle pagination testée séparément dans `work/layout-v4-smoke` : kit trois pages accepté, phase quatre pages accepté sans gain de lisibilité démontré face aux trois pages précédentes. Notes, tempos, compression et MIDI conservés ; aucun run figé modifié.

Correction des intervalles d'extrapolation aux bords de la grille, légende plus
claire et réserve de titre/légende dans la pagination. Aucun nouveau filtrage
pédagogique ni suppression de nuances. Six essais enregistrés sur treize ;
sept restent disponibles, piece_02 n'a pas été utilisé. Boucle arrêtée après
ces deux comparaisons ; F1 N/A, aucune meilleure méthode désignée. Recherche
et licences : `docs/detection-v4.md`, `docs/kit-detection-experiment.md`.

148 tests passent (9,01 s). Parcours navigateur réel vérifié sur piece_01 :
progression terminée, aperçu chargé et PDF/MusicXML/MIDI téléchargés. Traitement
local `fa0c0f2b3a80475eb1f4e9be35c28362`, 5,80 s avec cache et une reprise
MuseScore. Sous-agent isolé : toutes les trois pages acceptées comme brouillon
lisible, percussion seule, 1 147 attaques XML correspondant aux 1 162 coups
quantifiés après 15 collisions déclarées. Hash PDF/production concordant ;
feedback `work/verification/musical-v4/app-output/feedback-public.json`.
Capture `work/product-simplified-v4.png`. Le profil de détection
produit reste Demucs/ADTOF avec grille librosa, marqué brouillon. Prochaine
étape : valider la phase et les confusions locales avec une référence alignée
via le chat ; les diagnostics d'activation ne remplacent pas cette validation.

## Corpus externe et validation inspectable — historique avant le handoff

Dix compositions multi-instruments d'auteur sont acquises avec leurs MIDI
originaux sous CC0 : cinq auteurs, 16,13 minutes. Audit indépendant des licences,
hashes, conversions et correspondances structurelles terminé : dix entrées
admises, aucune référence encore évaluable. Un candidat incohérent a été
remplacé avant inférence. Inventaire et limites : `docs/corpus.md` ; feedback
public `work/corpus-quality.json`. Il s'agit de fichiers entiers publiés, souvent
des musiques de jeu ; le caractère non bouclé n'est établi que pour deux pièces.
Le supplément de dix performances GMD batterie seule reste distinct.

La recherche ne charge que `data/benchmark-research-manifest.json`. Les MIDI et
candidates non quantifiées restent côté vérificateur. Une première baseline
audio seule, profil unique `configs/baseline.json`, a produit dix chaînes
complètes et 25 pages PDF, avec intégrité contrôlée séparément. Première passe :
neuf succès et un abort MuseScore ; une seule reprise du cas concerné avec le
même profil et le cache a réussi. L'échec est conservé dans les journaux.
Elle ne touche ni les quatre essais de piece_01 ni le contrôle piece_02. Fidélité
N/A, aucun réglage ni meilleure méthode annoncée. Sous-agent distinct : les
25 pages sont inspectées, batterie seule et intégrité validée ; dix brouillons
rejetés pour présentation pédagogique (légende manquante, un texte coupé,
sept dernières pages trop peu remplies). Une seule variante de présentation
a corrigé légende, reprise et équilibre des pages, sans changer les événements
ni la grille : huit PDF (18 pages) sont acceptés comme brouillons lisibles par
le sous-agent. Deux cas restent en échec MuseScore natif après les reprises
bornées ; leurs anciens PDF ne servent pas de remplacement. Baseline conservée
dans `work/benchmark-v1-final.json`, états courants `work/benchmark-results.json`,
avis public `work/benchmark-presentation-feedback.json`. Invariance des JSON,
MIDI et grilles contrôlée par hashes ; expansion XML contrôlée indépendamment.
La boucle est arrêtée après cette variante. Rapport `docs/benchmark-presentation.md`.

L'onglet `/verification` présente désormais la source et la saisie candidate en
notation musicale, avec choix des mesures, zoom, audio et décisions partielles
privées. Les trois pages source de piece_01 sont visibles, seule la première
est numérisée ; aucun alignement audio n'est supposé. Les vues des dix MIDI
sources sont des projections de lecture clairement distinctes de la vérité
symbolique originale. Les huit PDF moteurs courants et leurs aperçus sont
consultables dans un panneau distinct ; les deux échecs sont affichés clairement.
L'avis de lisibilité n'apparaît que si son morceau et son hash PDF concordent.
Les confirmations ne promeuvent jamais automatiquement
une référence complète. Voir `docs/human-review-interface.md`.

Audit code indépendant : `docs/corpus-integration-review.md`, budgets de tout
le batch contrôlés avant inférence. 106 tests passent, preuve
`work/tests-corpus-delivery-final.log` ; contrôles synthétiques, pas benchmark musical.

Prochaine action technique : stabiliser l'export PDF natif, sans relancer de
variantes musicales tant que les références ne sont pas validées et alignées.
L'interface permet cette qualification humaine sans modifier les prédictions.
Capture de lecture réelle : `work/validation-interface-final.png`.

## Recherche poursuivie — boucle v3

Fidélité actuelle : N/A. Quatre essais de développement enregistrés sur treize, dont un échec de rendu ; neuf essais restent disponibles. Aucun essai de contrôle. Trois baselines complètes ont maintenant été figées et contrôlées par sous-agent en contexte distinct :

| Méthode | Run | Coups bruts | Pages | Retour indépendant |
|---|---|---:|---:|---|
| ADTOF mix | 20261010T094216-38f99831 | 1 188 | 3 | Brouillon lisible accepté |
| Demucs → ADTOF | 20261010T092826-05720728 | 1 162 | 3 | Brouillon lisible accepté |
| DrumScript mix | 20261010T094832-90460d7c | 989 | 4 | Rejet pédagogique : dernière page trop vide |

L’intégrité des trois sorties est passée ; aucune F1 musicale calculée et aucune méthode retenue comme meilleure. Le nombre de coups ne mesure pas la fidélité. Nouveau mix : 4,32 s avec cache ; DrumScript : 38,01 s, DSP sans poids appris ni séparation, 123 labels inconnus exclus explicitement et conservés dans le résultat brut. Rapport public : `work/research-v3-results.json`, état agrégé `work/research-progress.json`.

La première page de la référence manuelle est numérisée côté privé (16 mesures écrites). Paquet humain `work/verification/reference-preparation-v3/validation-humaine.pdf` ; aucune prédiction consultée pour cette saisie. Numérisation candidate et secondes non validées ; les drapeaux restent false. Contre-vérification indépendante terminée : candidate_ready_for_human_review ; une erreur certaine de saisie, une certitude documentaire et un défaut de rendu corrigés, paquet de six pages relu. Huit groupes de confirmations humaines subsistent. Pages restantes et alignement indépendant restent à préparer. Aucun événement attendu n’a été transmis à la recherche.

`cycle --resume-run IDENTIFIANT` reprend une sortie figée sans réinférence. Audio, configuration, pièce, nature synthétique, statut, gel de contrôle et budget sont contrôlés ; intégrité invalide ou avis manquant interrompt la sélection. L’évaluateur et le schéma refusent toute référence réelle non validée humainement ou non alignée indépendamment. Revue indépendante et tests de régression : `docs/loop-review-v3.md`. 83 tests complets passent, preuve `work/tests-final-v3.log`.

Une seule hypothèse audio est proposée, non exécutée : ajustement robuste de la grille sur fenêtres de huit beats. Aucun seuil optimisé sans mesure évaluable. Prochaine action : validation humaine du paquet et alignement audio indépendant pour scorer le passage explicitement couvert ; pas de pourcentage global extrapolé depuis une page.

## Livraison et preuves

- Une chaîne audio seule : contrôle d’entrée → Demucs CPU → ADTOF → grille depuis le mix → MIDI quantifié → MusicXML percussion → PDF MuseScore. Aucun accès aux feuilles manuelles.
- Interface locale `drum-lab serve --port 8765`, sélection audio, progression, aperçu PDF, téléchargements PDF/MusicXML/MIDI quantifié/brut et hypothèses visibles. Génération réelle réussie depuis le navigateur : jobs `dbf3f23367404b5ca1ccf4900b79bf7e` et `c9847e843a1d45eb9b7b404b60da3178` ; téléchargements réels des trois formats vérifiés par hashes. Aperçu première page PNG réel vérifié après correction du lecteur PDF noir dans IAB, job `c38630efb1f1447caa4946f051b6846f` ; capture `work/interface-final.png`.
- Nettoyage : un moteur de notation actif (`engraving.py`), anciens plans sous `docs/archive`, `STATUS.md` pointe vers ce document ; clone tiers incomplet retiré. Code, données, recherche et vérification ont des emplacements distincts.
- 83 tests réussis : matching, doublons, couverture simplifiée, absence de fuite, quantification, notation, contrôles d’intégrité, refus d’une sélection sans avis indépendant, entrées/erreurs/isolation HTTP et téléchargements. Les fixtures synthétiques vérifient le logiciel uniquement.
- Séparation réelle Michael : 89,50 s CPU la première fois, puis cache ; modèle et poids épinglés dans `configs/demucs-model.json`, dependencies isolées.
- Deux premiers essais complets documentés : mix `20261010T092819-d0f287ce` échoué au rendu natif MuseScore ; séparation `20261010T092826-05720728` rendu réussi. Registre `work/research-v2-results.json`. Aucun verdict de supériorité musicale.
- Sortie figée du second run : 1 162 coups bruts et quantifiés ; 1 147 coups gravés après 15 collisions du même instrument explicitement déclarées ; PDF 3 pages. `outputs/piece_01` pointe vers ce run, sans copie concurrente. Ancienne livraison 6 pages conservée dans `work/archive/`.
- Sous-agent en contexte isolé : les trois pages inspectées, batterie uniquement, aucun élément coupé ni collision visible. Verdict `accepted_as_readable_draft`, lié aux hashes dans `agent-feedback.json`. Rapport détaillé privé, feedback agrégé seulement. Vérificateur machine : intégrité passée ; fidélité N/A ; grille brouillon.
- Quantification : déplacement médian 40,3 ms, maximum 86,2 ms, 200 coups déplacés de plus de 50 ms. Ces chiffres constituent des diagnostics, pas une validation musicale. XML/MIDI vérifiés indépendamment après origine temporelle déclarée (écart maximal ~1,66 ms dû notamment à la sérialisation MIDI).

## Vérification et boucle d’optimisation

`run` ne connaît aucune référence. `cycle` confie les artefacts à un processus séparé ; le sous-agent Codex reçoit un contexte neuf et les références exclusivement côté vérification. La sélection est bloquée tant que la lisibilité indépendante et les métriques ne sont pas disponibles. Le CLI ne crée pas automatiquement d’agent IA. Isolation logique/procédurale sur disque partagé, pas sandbox OS.

Les deux partitions manuelles sont confirmées **simplifiées pour l’apprentissage**. Politique v2 : absence évaluable seulement dans les passages/classes explicitement validés comme tels ; détails supplémentaires hors périmètre comptés séparément, précision/F1 N/A si leur périmètre est incomplet. Politique v1 conservée comme historique.

Les originaux des deux paires sont présents, copiés avec hashes. Manifeste privé : `data/manifest.json` ; manifeste audio seul : `data/research-manifest.json`. Validation humaine des références symboliques et alignement indépendant encore absents ; aucun score musical réel, aucun réglage sur piece_02, aucun réentraînement. Deux pièces ne prouvent pas la généralisation.

## Limites et prochaine action

La partition est un brouillon exploitable pour révision, pas encore une fiche définitive pour élèves. Ajouter une légende du kit dans l’édition pédagogique ; valider grille, premiers temps et passages ambigus. La surdétection ne peut pas être certifiée absente avant cette comparaison. Swing, triolets et changements de signature ne sont pas inférés ; structure musicale scorée N/A.

MuseScore a présenté un abort natif intermittent : rendus sérialisés et au plus trois tentatives seulement pour cet abort, logs conservés. Export XML→MIDI natif non validé ; le MIDI livré vient directement de la quantification. All-In-One reste bloqué par son import madmom/pkg_resources ; DrumScript reste expérimental sans benchmark réel. Licences et versions : `docs/tools.md`.

Prochaine étape : côté vérificateur, numériser les annotations explicites et leur couverture, faire confirmer ces données par l’humain, puis fixer l’alignement depuis audio/référence sans consulter les prédictions. Scorer alors les sorties conservées, formuler une hypothèse ciblée sur piece_01, réutiliser les caches et conserver/rejeter selon score et lisibilité. Maximum 12 variantes après baseline ; contrôler piece_02 uniquement après gel.
