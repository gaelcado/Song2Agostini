# Audit indépendant de l’intégration du corpus et de l’interface privée

Audit du 10 octobre 2026, limité au code et aux fixtures synthétiques. Aucun
contenu de `data/raw/scores`, `data/reference`, `work/verification` ni de
manifeste privé n’a été lu. Le contrat `docs/separation.md` a été appliqué.

## Verdict

Les interfaces inspectées respectent la séparation logique prévue : le batch
ne passe que l’audio enregistré, le profil et l’identifiant à `run`; son worker
de contrôle reçoit seulement le dossier du run, sans référence. Les moteurs
ne reçoivent ni partition manuelle ni décisions de l’interface privée.
L’évaluation publie une projection explicite des métriques et des comptages
par fenêtre de dix secondes, sans événements attendus ni erreurs individuelles.
Les erreurs de vérification du CLI restent dans les journaux privés.

Les sorties du batch sont des contrôles d’artefacts, pas une mesure de fidélité
musicale : `reference_used` reste faux, `musical_fidelity` et `best_method`
restent nulls. Une grille et une partition générées ne valent pas validation.
La boucle refuse de choisir un run sans intégrité valide, score évaluable et
revue indépendante compatible avec les artefacts figés.

## Contrôles et correction

- Identifiants de corpus fixes, exclusion des doublons et au plus dix cas par
  batch; profil unique. Chaque audio doit correspondre à sa copie enregistrée,
  rester sous `data/raw/audio` après résolution et conserver son hash.
- Correction de `benchmark.py` : le budget de tous les cas est maintenant
  contrôlé avant la première inférence. Auparavant, un cas tardif à treize
  essais provoquait l’arrêt après avoir consommé un essai sur les cas précédents.
  Le type du profil et son hypothèse sont également contrôlés avant lancement.
- Serveur lié exclusivement à `127.0.0.1`; validation de Host, Origin et
  Sec-Fetch-Site. Les décisions POST exigent cookie de session et jeton associé.
  Taille des corps bornée; documents privés servis par clés autorisées et
  chemins résolus confinés; aucune route de fichier arbitraire.
- Les téléchargements de transcription sont attachés à leur session. Les
  aperçus restent dans le traitement. Les commentaires utilisent des nœuds de
  texte, sans insertion HTML.
- Les décisions humaines sont privées, versionnées par hash du candidat et
  limitées à la sélection. Les champs envoyés `human_validated=true` ou
  `alignment_fixed=true` ne peuvent promouvoir une décision : les valeurs
  enregistrées et publiées restent fausses. Le candidat n’est pas modifié.
- Relecture finale des assets : les scripts de préparation copient les sources
  dans la vue privée et enregistrent les SHA-256 des documents, audio et sorties
  moteur. `document()` les contrôle avant lecture; `save()` contrôle tous les
  assets hashés avant d’enregistrer une décision. Le risque de substitution de
  document décrit dans l’audit initial est résolu pour les vues préparées.
- Les PDF moteur et aperçus empruntent les mêmes routes privées autorisées et
  les mêmes contrôles de hash et de chemin. La synchronisation prend les runs du
  rapport de corpus et valide leurs identifiants; un cas en échec enregistre
  explicitement l’absence de PDF et supprime ses anciennes copies. Une correction
  supplémentaire donne priorité à l’état `failed`, même si des clés de fichiers
  anciens restent dans le registre : aucun repli sur ces fichiers n’est proposé.

Preuve exécutée : `.venv/bin/python -m pytest tests/test_benchmark.py
tests/test_separation.py tests/test_human_review.py tests/test_ui.py
tests/test_pipeline.py -q` → **52 tests réussis** après relecture finale. Ces tests couvrent notamment
le refus du batch avant toute inférence si un cas tardif a épuisé son budget,
les profils invalides, les hashes, les sessions, CSRF, traversées de chemins,
le filtrage du feedback, les reprises de runs figés, les substitutions d’assets,
les sorties moteur hors dossier et l’échec avec ancien registre persistant. Ce n’est pas un
benchmark musical et aucune inférence réelle n’a été lancée pour cet audit.

## Limites concrètes

1. La séparation est logique, sans sandbox OS ni ACL de rôle. Toute session
   locale valide peut consulter les vues de vérification; l’interface n’est
   pas une protection contre un autre processus ou agent ayant accès au disque.
2. Le budget repose sur les `record.json` persistants et sur une exécution CLI
   séquentielle. Deux commandes lancées simultanément peuvent faire leur
   précontrôle avant l’écriture de l’autre; aucune réservation atomique globale
   ne garantit le plafond dans ce scénario. La suppression des journaux retire
   aussi des essais du décompte.
3. Les contrôles SHA-256 des documents restent facultatifs pour compatibilité
   avec les anciens registres : les vues préparées par les scripts actuels
   les fournissent toutes. Un ancien registre sans hashes doit être régénéré
   pour bénéficier de cette protection. Les métadonnées elles-mêmes restent
   modifiables par un processus ayant accès au disque, selon la limite logique
   décrite au point 1.
4. Le batch et `run` contrôlent l’enregistrement des audios du corpus; la
   commande générale `transcribe` appelle directement le pipeline. Lui donner
   un identifiant de corpus n’établit donc pas la correspondance ID/hash d’un
   benchmark enregistré. Ses sorties ne doivent pas être présentées comme un
   run de corpus contrôlé.

Prochaine action : garder les références sous le rôle vérificateur, compléter
les décisions humaines sans en déduire une validation complète, puis exécuter
les profils figés. Si des lancements simultanés sont nécessaires, ajouter une
réservation atomique du budget avant de les autoriser.
