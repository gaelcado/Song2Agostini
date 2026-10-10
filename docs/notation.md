# Partition batterie issue de la recherche

La sortie principale est le PDF, accompagné du MusicXML éditable, du MIDI brut
intact et du MIDI quantifié distinct. Aucune feuille manuelle ne participe à
l'estimation de grille, à la quantification ou à la gravure.

## Grille audio et hypothèses

L'estimateur librosa utilise `trim=True`, puis retire les pulsations sans activité
RMS locale. L'origine proposée est la première pulsation suivie audible, jamais
un zéro ajouté artificiellement. C'est une hypothèse de premier temps, pas une
reconnaissance de downbeat : la signature 4/4, l'octave du tempo et les doubles
croches restent provisoires. Le tempo est ramené à l'octave inférieure au-delà
de 160 BPM, par règle audio générale. Les silences intérieurs gardent leurs
positions musicales grâce à un comptage explicite des pulsations manquantes
quand les intervalles dépassent 1,8 fois la médiane. Cela suppose un tempo
approximativement stable dans ces silences. Les bords utilisent une extrapolation
explicite, sans ajouter de faux beats à la liste détectée.

Les événements avant l'origine sont conservés en ajoutant des mesures complètes
à la grille ; le rapport en indique le nombre. Ce préambule est provisoire,
il ne prouve pas une anacrouse. Le rapport `quality` donne déplacement médian,
maximal, nombre de déplacements >50 ms et collisions de même instrument. Ces
mesures décrivent la quantification, pas la fidélité à une référence.

## Gravure compacte et conservation

`engrave(midi_path, grid, out, title, compact=True)` produit par défaut des
reprises de blocs consécutifs **strictement identiques** (jusqu'à 16 mesures par
bloc). Le nombre de passages est explicite. Les numéros des mesures conservées
sont ceux du déroulé original ; les plages comprimées sont écrites au-dessus
de la reprise. Un fill différent empêche la fusion ; une carte de tempo différente aussi. Chaque
mesure comporte quatre directions de tempo, une par noire, pour préserver la
variation locale au lieu d'une moyenne par mesure. Les silences consécutifs
reçoivent un `multiple-rest` MusicXML ; leurs mesures sous-jacentes restent
présentes pour garantir la conservation. Le rendu dépend du support de cette
indication par MuseScore. `compact=False` fournit le déroulé intégral.

Portée de percussion, charleston/cymbales en voix haute et fûts en voix basse,
accords pour les attaques simultanées. Les autres pistes MIDI sont ignorées avec
avertissement ; les percussions hors mapping GM pris en charge sont refusées.
Aucune note mélodique `<pitch>` n'est créée. Les collisions même pitch à la même
case sont fusionnées uniquement dans la notation ; le MIDI quantifié garde
chaque événement, et le MIDI brut reste intact.

Un audit lit les durées, instruments et reprises du MusicXML final, vérifie les
16 unités de chacune des deux voix puis redéveloppe les reprises. Il exige
l'identité exacte des attaques `(case, pitch)` avec la notation quantifiée
(après regroupement explicite des collisions). `notation.json` conserve cet
audit, les segments de compression, les hashes et les diagnostics. Ce contrôle
ne valide ni le choix du premier temps, ni le tempo, ni la pertinence pédagogique
et ne constitue pas une comparaison musicale réelle.

## Exécution locale et limites

Le PDF est rendu par MuseScore local, épinglé dans `configs/musescore.json`.
Les sorties comprennent `score.pdf`, `score.musicxml`, `quantized.mid`,
`notation.json` et le log ; le contrat retourne aussi leurs chemins absolus.
Pas de service cloud. Swing, triolets, changements de signature et ornements
ne sont pas inférés. Un rythme irrégulier ou surdétecté peut fournir peu de
reprises exactes : la compaction n'invente pas de motifs réguliers et ne remplace
pas le nettoyage du moteur. Les sorties restent marquées brouillon automatique.

Le MusicXML utilise une horloge musicale relative. `musicxml_audio_offset_seconds`
donne son origine sur l'audio ; une introduction avant la première pulsation ou
un préambule peuvent produire un décalage absolu par rapport au MIDI, lequel
conserve les secondes audio. Les écarts maximal relatif et absolu sont enregistrés
dans `quality`, sans prétendre que les deux horloges commencent toujours à zéro.
Ces écarts sont calculés à partir des directions de tempo XML, pas d'un export
MIDI de lecture MuseScore. Le rendu PDF et l'audit XML ne garantissent pas le
playback d'un logiciel tiers ; l'essai d'export MIDI MuseScore de la nouvelle
version a échoué avec SIGABRT/mutex, malgré le rendu PDF réussi.

## Pagination et espace de première page

La version `kit-legend-first-page-capacity-v3` réserve explicitement l’espace
du titre, de l’avertissement et de la légende sur la première page. Le budget
est de six groupes de systèmes sur les pages suivantes ; la première perd
un groupe par tranche de 180 unités MusicXML occupées par la légende. Avec
cinq instruments, elle accueille au plus cinq groupes. Les groupes restants
sont répartis avant d’émettre les sauts de page, afin d’éviter un débordement
automatique d’une seule portée juste avant un saut forcé. Les silences
multimesures ne consomment qu’une unité visible et aucun saut n’est placé dans
leurs mesures masquées.

Un groupe vise quatre mesures visibles ; MuseScore peut ajouter des portées
quand une mesure est dense. Le budget n’est donc pas un décompte garanti des
portées finales : contrôler le PDF rendu reste nécessaire. Aucun changement
d’événement, de grille, de MIDI quantifié ou de compression n’est associé à
cette correction.

Contrôle local sur les deux sorties automatiques déjà produites, sans nouvelle
inférence : `work/layout-v4-smoke/kit/score.pdf` contient trois pages (au lieu
de quatre dont une orpheline), `work/layout-v4-smoke/phase/score.pdf` quatre.
Les MIDI quantifiés sont identiques octet par octet ; grille, segments, attaques,
audit XML et diagnostics sont identiques aux runs figés. Les 36 tests de gravure
couvrent notamment les capacités de première page, les partitions denses et les
longs silences. Ces preuves vérifient la présentation et la conservation ; elles
ne constituent pas un gain de fidélité musicale.

## Convention française demandée (Agostini), version v5

La version `french-agostini-beat-beams-v5` utilise les positions françaises
illustrées par le pédagogue Claude Gastaldin sur
[Percunivers, notation de la batterie](https://www.percunivers.com/notation.php),
notamment sa [nomenclature française](https://www.percunivers.com/notation/notation_fr.png).
Le chapitre batterie de [Jean-Michel Tostivint, Notation musicale, p. 92–94](https://www.jmtostivint.fr/images/pdf/Notation-musicale.pdf)
confirme la caisse claire sur la troisième ligne, la grosse caisse sous la
première ligne, les deux voix et les ligatures par temps. Ces sources décrivent
une convention française compatible avec la demande Agostini ; elles ne
certifient pas une nomenclature exclusive ou universelle de cet éditeur.

| Famille commune | Position de gravure représentative | Tête et voix | Coordonnée interne MusicXML |
| --- | --- | --- | --- |
| kick | Sous la portée | Pleine, voix basse | D4 |
| snare | Ligne centrale (troisième ligne) | Pleine, voix basse | B4 |
| hi-hat | Au-dessus de la portée | Croix, voix haute | G5 |
| toms | Quatrième ligne (position médium) | Pleine, voix basse | D5 |
| cymbals | Ligne supplémentaire supérieure (position crash) | Croix, voix haute | A5 |

Ces coordonnées sont des emplacements graphiques sous `<unpitched>`, jamais
des notes de piano. Les pitches GM d'entrée et leurs secondes audio ne changent
pas. Pour un moteur à cinq familles, « tom médium », « crash » ou « charleston
fermé » sont des positions de représentation et des identifiants MIDI
conventionnels : aucune distinction de registre, ride/crash ou ouverture n'est
inférée par cette gravure. Les sorties d'un moteur plus fin peuvent conserver
leurs pitches déjà fournis : tom grave A4, tom aigu E5, ride B5 et pédale
charleston B3. La légende affichée décrit les instruments, les têtes et leur
position sur la portée avec des mots français.

Les cymbales main et le charleston main utilisent la voix haute, hampes vers
le haut ; grosse caisse, caisse claire et toms utilisent la voix basse, hampes
vers le bas. La pédale de charleston explicitement présente est en voix basse.
Chacune des deux voix complète chaque mesure de 4/4. Les durées restent
coupées aux frontières des temps. Des balises `<beam>` explicites groupent
croches et doubles croches à l'intérieur d'un temps, y compris un silence
intermédiaire ; aucune ligature ne traverse une pulsation. Les doubles croches
isolées dans un groupe utilisent une demi-ligature orientée vers une voisine.
Les notes d'accord suivantes ne portent pas de ligature redondante. Un temps
entièrement silencieux reste sans ligature.

Cette correction concerne uniquement la représentation, sans ajout,
suppression ou déplacement d'attaque et sans modification de la grille audio.
Les MIDI bruts et quantifiés ainsi que les directions de tempo sont préservés.
Les tests synthétiques de gravure (44 tests) couvrent les coordonnées, les deux
voix, les ligatures, les silences, les accords et la conservation des attaques ;
ils ne mesurent aucune fidélité musicale réelle.

Les anciennes inférences ont été représentées séparément dans
`work/agostini-v5/baseline` (3 pages) et `work/agostini-v5/phase` (4 pages),
sans modifier leurs runs figés. `work/agostini-v5/conservation.json` prouve
l'identité octet par octet des MIDI quantifiés, des diagnostics de quantification,
des segments de reprise et des directions de tempo. Les audits retrouvent
1147 et 1152 attaques respectivement et contrôlent sur le XML complet qu'aucune
ligature primaire n'est ouverte ou ne traverse un temps. Toutes les pages ont
été rendues en PNG et inspectées : titres, légendes et marges restent lisibles.
Les passages surdétectés conservent une écriture dense. MuseScore peut ignorer
certaines ligatures portées par les silences à l'import MusicXML et conserver
des crochets isolés autour de ceux-ci : la politique est explicite dans le XML,
mais le rendu ne garantit pas une ligature visuelle continue sur tout silence.
