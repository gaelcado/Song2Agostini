# Ajouts de charleston appuyés par des transitoires

L’option expérimentale `hat_transient_candidates` est désactivée par défaut.
Elle requiert ADTOF sur la batterie isolée et conserve tous les événements
initiaux. Elle examine uniquement les propositions supplémentaires obtenues en
abaissant le seuil charleston à 0,16 ; elle ne complète aucun motif rythmique.

Le flux spectral positif entre 5 et 16 kHz est calculé sur la batterie séparée.
Un candidat doit coïncider avec un pic à ±25 ms, dépasser le fond local de
3 écarts absolus médians normalisés et son percentile 90. Le contexte couvre
±0,5 seconde. Un pic ne peut soutenir qu’une frappe : les charlestons initiaux
réservent d’abord leurs pics, puis les candidats sont examinés dans l’ordre.
La proximité d’une cymbale initiale à ±70 ms entraîne une abstention.

Ces critères décrivent des transitoires, pas une identité instrumentale prouvée.
La séparation peut introduire des artefacts. Une cymbale et un charleston peuvent
être joués ensemble : cette règle prudente peut donc refuser un ajout légitime.
Aucune frappe initiale n’est supprimée ou reclassée.

Chaque run préserve `detector-raw.mid` et `detector-events.json` avant ajout.
`raw.mid` et `events.json` contiennent la candidate complète ;
`transient-audit.json` conserve les empreintes, paramètres et décisions pour
chaque proposition. Les vitesses et placements initiaux restent conservés.
La production signale explicitement le caractère expérimental de ces ajouts.

Les tests logiciels couvrent silence, bruit stationnaire, sinus stable,
transitoires, gain, types audio entiers/flottants, limites de signal,
ambiguïtés cymbales, unicité du pic de soutien et conservation du MIDI détecteur.
Ils ne constituent pas un benchmark musical. Le contrôle indépendant doit
repartir du mix original et distinguer corroboration énergétique et confirmation
du geste instrumental ; davantage de notes ne démontre pas un meilleur rappel.

Les flas ne sont pas inférés par cette option. Deux pics proches peuvent décrire
plusieurs gestes, et ne justifient pas seuls une appoggiature sur la partition.
