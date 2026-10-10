# Contrat de validation des artefacts finaux

Le vérificateur reçoit un dossier figé, ses hashes et un identifiant de morceau.
La recherche produit ce dossier à partir de l’audio sans référence. Les observations
détaillées du vérificateur restent sous `work/verification/` ; seule une projection
par allowlist est transmise à la recherche selon `docs/separation.md`.

## `verify-final` : contrôles indépendants des références

1. Ouvrir JSON, MIDI brut, grille, MIDI quantifié, MusicXML et PDF ; contrôler les
   identifiants, hashes, provenance et statuts de brouillon.
2. Vérifier une notation de percussion : canaux/pitches pris en charge dans les MIDI,
   éléments `unpitched`, clé percussion et mapping explicite dans le MusicXML.
3. Comparer décomptes et pitches JSON/brut/quantifié/XML ; déclarer toute suppression,
   fusion de doublons ou transformation. Vérifier les durées de chaque voix et la
   correspondance des positions musicales avec la grille.
4. Rapporter séparément les déplacements de quantification et les différences de
   playback XML/MIDI. Conserver le brut ; une grille non vérifiée reste brouillon.
5. Rendre chaque page PDF et l’inspecter : glyphes, collisions, marges, numérotation,
   densité, silences et compactage. Une exportation réussie ne prouve pas la lisibilité.

## Contrôles privés avec référence

La référence doit avoir une numérisation validée humainement, un mapping, un masque
de couverture/exhaustivité et un alignement indépendant des prédictions. Sinon,
les métriques musicales sont `null` avec la raison explicite. Un agent ne peut pas
attribuer `human_validated=true`. Comparer événements à 50 et 25 ms avec matching
un-à-un, puis placement musical, structure et breaks uniquement où ils sont annotés.
La comparaison visuelle seule ne fournit ni F1 ni vérité temporelle.

## Retour public autorisé

Hashes des artefacts prédits, succès/échec générique des contrôles, statistiques
des seules prédictions, diagnostics de rendu agrégés, statut brouillon, métriques
et erreurs agrégées autorisées par `docs/separation.md`. Aucun événement attendu,
alignement privé, motif de référence, correction de partition ou détail d’erreur
individuelle. Le rapport privé peut contenir ces détails mais ne traverse pas le
retour recherche. La séparation est logique dans un disque partagé.

La validation comporte des verdicts distincts : intégrité des formats, lisibilité,
fidélité musicale et grille. Aucun score opaque ne mélange ces dimensions.

## Références simplifiées : périmètre par passage

Les deux feuilles sont confirmées simplifiées pour l’apprentissage par l’utilisateur.
Pour chaque classe et passage, le vérificateur garde un masque validé humainement :
événements explicites, absence effectivement évaluable, coups supplémentaires hors
périmètre et zones ambiguës. Ne pas convertir l’absence d’une note écrite en FP par
défaut. Le rappel peut porter sur les événements explicites correctement alignés ;
précision/F1 nécessitent aussi un périmètre où l’absence est évaluable. Les zones sans
ce périmètre restent N/A et leurs coups supplémentaires sont comptés séparément.

## Acceptation pédagogique distincte

- Intégrité : zéro fichier manquant/inouvrable, zéro instrument mélodique, zéro
  transformation non déclarée entre les artefacts.
- Rendu : zéro collision, glyphes manquants ou élément coupé après inspection de
  toutes les pages ; chaque mesure et voix est exploitable dans l’éditeur.
- Compactage : regrouper les longues suites de silences entièrement vides sans
  modifier les événements ; éviter une page finale presque vide lorsque le moteur
  de mise en page permet une redistribution lisible.
- Clarté : légende du kit, portée de batterie, numéros et statut brouillon visibles.
  Le compactage ne supprime aucune frappe et n’introduit aucun motif de référence.
- Grille : origine, signature, tempo et subdivisions documentés ; aucun seuil de
  déplacement temporel ne remplace une validation du placement musical.

Ces critères de rendu peuvent être acceptés avant la fidélité musicale. Ils ne
fixent pas un seuil F1 arbitraire et ne rendent pas une grille automatiquement
validée. Les premiers temps et la référence demandent toujours un contrôle dédié.
