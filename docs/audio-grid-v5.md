# Grille audio v5 — diagnostic et correction bornée

Le défaut du tracker librosa prenait sa première pulsation audible pour un début de mesure, sans inférer le premier temps. Beat This prédit les premiers temps indépendamment des instruments, mais son postprocesseur minimal conservait 26 doubles pics séparés de 80–100 ms sur `piece_01`. Le quantificateur les comptait comme des temps supplémentaires : la phase dérivait après environ 63 secondes.

La règle `merge_close_model_peaks_v1` fusionne les groupes de pics distants de moins de 0,35 période médiane. Elle conserve un pic effectivement observé, celui le plus proche du milieu temporel des groupes voisins. Les downbeats sont rapprochés de la pulsation retenue puis dédoublonnés. Aucun événement batterie, aucune hauteur MIDI ni aucune référence n'intervient. Les listes brutes restent dans la grille. La règle est idempotente et ses tests couvrent tempo rapide, intervalles de demi-pulsation, signature discordante et cache incompatible.

Cette politique suppose des doubles pics plutôt qu'un changement de tempo extrême sur quelques pulsations ; elle ne démontre pas l'exactitude musicale. Les groupes transitoires très serrés peuvent donc rester ambigus. En cas de désaccord des downbeats locaux avec quatre temps par mesure, le logiciel signale le problème et conserve le brouillon sans forcer une phase 4/4.

Sur la grille audio mise en cache, 337 pulsations deviennent 311 et 83 premiers temps deviennent 78. Les 77 intervalles entre premiers temps contiennent alors exactement quatre pulsations, tous de même phase. L'origine reste 0,92 s. Les hypothèses de signature et la phase restent non validées humainement.

Un seul nouvel essai a été enregistré : `20261010T104109-a75f54de`, configuration `configs/phase-beat-this-v5.json`. Il réutilise séparation, activations ADTOF et grille Beat This, avec contrôle des hashes audio et modèle. Temps total : 6,89 s. Les 1 162 événements bruts sont inchangés. La nouvelle gravure utilise le mapping pédagogique français ; elle ne change pas les pitches GM.

Quantification : déplacement médian 20,45 ms, maximum 74,55 ms, 29 coups au-delà de 50 ms, 11 collisions préservées. Ce sont des diagnostics de déplacement, pas des scores de fidélité.

Numérotation issue uniquement de cette grille : mesure 8 = 19,58 s, mesure 11 = 27,60 s, mesure 12 = 30,26 s. Le premier événement détecté est à 26,909 s. L'ancienne édition avec origine 10,983 s plaçait sa mesure 8 vers 29,65 s : les numéros ne désignent donc pas le même passage entre éditions. Des silences introductifs font partie de la sortie et leur présence ne signifie pas que le tracker a trouvé de la batterie.

Les nouveaux audios suivent la même chaîne : modèle Beat This épinglé → nettoyage → MIDI quantifié → MusicXML → PDF. Le cache de `piece_01` sert seulement à cet essai. Aucun fallback silencieux ne remplace un modèle indisponible.

Le contrôle musical et visuel indépendant reste nécessaire. Aucune partition manuelle n'a été consultée par la recherche. `piece_02` n'a pas été utilisé. Budget de développement porté de 6 à 7 essais sur 13 autorisés, puis arrêt pour vérification.
