# Revue indépendante de la boucle — 10 octobre 2026

Périmètre : `optimization.py`, routage CLI `--resume-run`, évaluateur et schéma
événementiel, classement `runner.py`, liaison registre/production dans
`final_verification.py`, tests publics. Aucun manifeste privé, référence, partition manuelle
ou contenu de `work/verification/` consulté. Revue de code et fixtures synthétiques ;
aucune mesure de fidélité musicale réelle.

Corrections ciblées :

- Une reprise accepte seulement un run terminé (`awaiting_verification` ou
  `failed`) ; un run encore `running` est refusé avant la vérification.
- Le contrôle repris `piece_02` doit toujours correspondre aux paramètres
  actuellement gelés. Le résultat indique correctement ce gel.
- Le budget global des treize inférences est vérifié avant la boucle ; reprendre
  une sortie seule ne dépense pas un nouvel essai, ajouter un candidat le fait.
- Un rejet d’intégrité interrompt la boucle avec son motif propre. Son score est
  N/A et le candidat ne peut pas être sélectionné.
- Le schéma impose `human_validated=true` et `alignment_fixed=true` pour les
  références réelles, y compris quand `synthetic` est omis. Les fixtures
  synthétiques gardent leur exemption. Les erreurs explicites de l’évaluateur
  sont conservées.
- Le classement purge tout ancien `macro_f1_50ms` avant lecture du feedback
  actuel : score absent, feedback invalidé ou revue manquante ne peut conserver
  un ancien rang. Un feedback valide remplace aussi le score ancien.
- Le vérificateur lie un registre présent au dossier et à la production :
  identifiant, pièce, hash audio, nature synthétique, statut figé et paramètres.
  La production peut inclure des valeurs par défaut supplémentaires ; les
  paramètres explicitement enregistrés doivent correspondre.

Preuve : `.venv/bin/python -m pytest tests/test_pipeline.py
 tests/test_evaluation.py tests/test_separation.py tests/test_final_verification.py -q`
→ **57 tests réussis**. Les tests couvrent reprise sans inférence, mismatches
identifiant/audio/nature/pièce/configuration, run non figé, contrôle sans gel,
re-vérification au budget maximal, refus d’un nouvel essai hors budget et run
scoré mais invalidé, purge des scores anciens et liaison registre/production.
Les retours publics de boucle contiennent uniquement IDs,
décisions et macro-F1 ; aucune note de référence n’est ajoutée.

Limites : la séparation est logique, pas un sandbox OS. Une reprise dépend du
record figé et du vérificateur pour le contrôle des artefacts. La boucle ne
reprend pas automatiquement toutes les décisions d’un ancien cycle : sa liste
explicite de candidats définit les candidats comparés. Les tests ne constituent
pas un benchmark musical.
