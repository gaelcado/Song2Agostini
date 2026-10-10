# Triolets locaux : essai audio conservateur

L’option `local_tuplets` (désactivée par défaut) compare les attaques déjà
prédites aux subdivisions binaires et aux tiers de noire dans une signature
simple. Deux tiers intérieurs distincts doivent être présents ; toutes les
attaques du temps doivent être à moins de 0,07 noire d’un tiers et le gain
moyen sur la grille binaire doit atteindre 0,035 noire. Aucune note n’est
ajoutée pour compléter un motif. Ce critère est un diagnostic non calibré,
ni une reconnaissance musicale validée ni une promesse de fidélité.

Une sélection locale fait utiliser 12 divisions par noire à toute la partition ;
les temps non sélectionnés conservent les positions de doubles croches. Les triolets affichent le rapport 3:2 et les
bornes du groupe, y compris lorsque le groupe débute par un silence. Les
signatures 6/8 et 12/8 conservent leurs groupes de trois croches ordinaires.
Le MIDI brut et les événements du moteur restent inchangés. Les collisions
même instrument restent signalées, sans création automatique de flas.

MusicXML distingue le rapport de durée
[time-modification](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/time-modification/)
et son affichage
[tuplet](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/tuplet/).
Les tests synthétiques contrôlent durée des deux voix, accords, silences,
ratio, bornes de triolets, ordre XML et conservation des événements. Ce sont des tests
logiciels, pas une évaluation musicale.

Les flas restent une limite de détection. Le PeakPicker ADTOF installé travaille
à 100 images/s, avec `pre_avg=.1`, `post_avg=.01`, `pre_max=.02`,
`post_max=.01`, `combine=.02`. Une attaque secondaire peut être absente des
prédictions avant la notation ; aucun symbole ne saurait la rétablir sans
preuve audio. La boucle bornée conserve séparément les diagnostics de paires
rapprochées, sans les qualifier automatiquement de flas.
