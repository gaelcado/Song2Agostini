# Inférence métrique depuis l’audio

## Problème observé

La grille historique fixait `time_signature=4/4` et quatre subdivisions par
pulsation. La gravure refusait toute autre signature. Les pulsations et premiers
temps de Beat This étaient des prédictions audio, mais la signature affichée
était une limitation d’export, pas leur résultat.

## Séparation et expérience bornée

Les audios seuls et les prédictions déjà calculées servent à la recherche.
Les feuilles humaines restent réservées au vérificateur isolé. Les coups bruts,
les entrées et les anciennes partitions sont préservés. Le traitement métrique
ne doit jamais ajouter les notes attendues d’une feuille.

Plan privé préenregistré : `work/meter-audio-20261010/preregister.json`.
Baseline historique puis au plus trois variantes générales, sans règle par titre.
La première examine le cycle entre premiers temps et les phases des pics de flux
spectral. La seconde sépare l’évidence de subdivision de celle du cycle : une
subdivision ternaire claire ne doit pas être convertie en binaire simplement
parce que le regroupement global des mesures est incertain.

Les parts de poids de pics proches des phases binaires ou ternaires sont des
diagnostics descriptifs. Ce ne sont pas des probabilités calibrées de justesse.
Une erreur de pulsation, une moitié de mesure prise pour une mesure, le swing,
les changements de métrique et les passages pauvres en attaques peuvent rester
ambigus. Une notation composée et une notation simple avec triolets peuvent
représenter des choix d’écriture proches : l’audio ne garantit pas le choix de
la feuille humaine.

La signature, les subdivisions, l’unité de tempo, les durées MusicXML et les
ligatures doivent être cohérentes. Modifier seulement le chiffre affiché ne
corrige pas une grille. Les déplacements de quantification et collisions sont
comparés avant/après ; ils ne constituent pas un score de fidélité musicale.

## Sources techniques

- [Beat This!, implémentation officielle](https://github.com/CPJKU/beat_this) :
  estimation des pulsations et premiers temps, sans résoudre tous les choix
  de notation musicale.
- [MusicXML, signature temporelle](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/time/).
- [MusicXML, unité pointée du métronome](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/beat-unit-dot/).

## Validation

Les fixtures synthétiques vérifient les durées, les subdivisions, l’intégrité
et l’absence de fuite de référence. Les nouveaux PDF doivent être contrôlés
séparément sur toutes leurs pages. Les annotations de signature visibles sur
les feuilles ou confirmées par l’utilisateur ne constituent pas un alignement
audio validé. La fidélité des événements reste N/A tant que cet alignement et
la transcription symbolique de référence ne sont pas validés humainement.

## Résultat de la passe du 10 octobre

La dernière variante conserve six doubles croches par pulsation pointée au lieu
de trois croches seulement. La variante grossière a été rejetée parce qu’elle
regroupait davantage d’attaques. Pour le cas composé, le déplacement médian est
passé de 19,5 à 10,9 ms sans augmenter les collisions. Les quatre autres cas
conservent leurs diagnostics. Les coups bruts n’ont pas changé.

Les cinq exports ont passé un contrôle indépendant d’intégrité et de lisibilité
sur 27 pages. Comparaison de signatures écrites : trois concordances globales,
une partielle, une divergence majeure. Les changements locaux ne sont pas
encore représentés ; le choix du niveau de pulsation et les équivalences de
notation restent limités. Cette passe est du développement, pas une preuve de
généralisation ou de fidélité musicale.
