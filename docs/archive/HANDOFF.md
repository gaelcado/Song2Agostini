# Contexte transmis — 10 octobre 2026

L'utilisateur souhaite créer un nouveau projet Codex sur son ordinateur et y poursuivre le travail. C'est un projet pour un apprenant. Il fournira deux entrées audio et deux partitions de batterie faites à la main, chacune liée à son audio. Le critère central est une boucle d'expérimentation comparant solutions et processus pour maximiser la fidélité mesurée.

Aucun des quatre fichiers n'a encore été fourni. Leur format, genre, durée, exhaustivité et précision temporelle restent inconnus. Ne pas chercher ces fichiers dans des dossiers personnels sans indication. Préparer l'infrastructure maintenant, puis documenter leur dépôt.

La recherche précédente recommande ADTOF-pytorch pour audio → MIDI et All-In-One pour structure. Il s'agit d'une recommandation documentaire, pas d'un benchmark déjà exécuté. Demucs sert à isoler la batterie, pas à la transcrire. La séparation peut introduire des artefacts. Une bonne partition demande ensuite un travail de grille, quantification et notation.

Sources consultées:
- https://github.com/xavriley/ADTOF-pytorch — CLI et API Python, poids intégrés; résultat publié F1 ~88,5 % sur MDBDrums++, ne pas transposer à nos morceaux.
- https://github.com/MZehren/ADTOF — modèle de recherche, licence CC BY-NC-SA 4.0.
- https://github.com/mir-aidj/all-in-one — tempo, beats, downbeats, sections et export JSON; dépendances NATTEN/madmom à vérifier.
- https://github.com/adefossez/demucs — séparation; ancien dépôt Meta archivé, maintenance limitée.
- https://github.com/DrumScript/DrumScript — Python/CLI, classification déterministe, PDF/MIDI/MusicXML, alpha avec limites déclarées.
- https://github.com/xavriley/adtof_plus_drum_transcription — séparation du kit et transcription enrichie, expérimental.
- https://github.com/DomekRomek/DrumLab — interface locale autour de Demucs et ADTOF.
- https://drumscrib.com/fr/ et https://drum2notes.klang.io/ — comparateurs propriétaires facultatifs, aucun achat ni upload autorisé par défaut.

Limitation de l'app: les outils permettent de créer un chat local avec son propre dossier, mais n'exposent pas la création d'un projet dans la barre latérale. Le contrôle UI de com.openai.codex a été explicitement bloqué. Ne pas contourner cette restriction par AppleScript, modification de l'état privé ou interfaces internes. L'utilisateur devra ajouter le dossier comme projet si cette capacité reste absente. Documentation: https://learn.chatgpt.com/docs/projects

Lire AGENTS.md et IMPLEMENTATION.md, commencer la mise en place, et rapporter le dossier absolu à ajouter dans Codex. Ne pas attendre les audios pour développer l'évaluateur, ses tests et le squelette des adaptateurs.
