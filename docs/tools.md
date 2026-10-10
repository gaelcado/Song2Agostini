# Moteurs vérifiés le 10 octobre 2026
Versions exactes et commits : configs/tools.json et configs/*.lock.txt. Environnements Python 3.11 séparés ; Python global inchangé. Mac arm64, 16 Go RAM.

- ADTOF-pytorch 0.1.0 : import, poids présents et inférences CPU synthétique et Michael vérifiés. MPS disponible dans PyTorch mais non proposé par cet adaptateur. Chargement strict des poids ; absence de poids = erreur, jamais réseau aléatoire.
- Demucs 4.0.1 : séparation Michael réelle vérifiée (89,50 s CPU), cache audio/poids/worker/dépendances. Worker local indépendant des API torchaudio récentes ; htdemucs 955717e8 épinglé par SHA-256 dans configs/demucs-model.json. soundfile 0.14.0 dans son environnement isolé ; aucune donnée audio transmise.
- DrumScript 0.2.1 : installation isolée et CLI --help vérifiées. Baseline DSP réelle sur mix Michael vérifiée en 38,01 s ; worker local préserve les événements bruts puis utilise la notation commune, sans séparation Demucs ni poids appris. 123 labels inconnus sont conservés et exclus explicitement. Cache épinglé sur audio, worker, lock et les 24 sources installées identiques au commit. Dépendances torch<2.9 et numpy<2 justifient son environnement séparé.
- All-In-One : package installé ; madmom absent de ses dépendances déclarées, ajouté manuellement. Import encore bloqué : madmom 0.16.1 dépend de pkg_resources absent du setuptools installé. D'autres incompatibilités anciennes ou NATTEN restent possibles. Adaptateur préparé mais moteur indisponible. Logs : work/allinone-import.log et work/install-madmom.log. Aucun poids de structure téléchargé ni carte de structure fabriquée.
- music21 : dépendance et implémentation concurrente retirées du projet actif. La nouvelle chaîne `engraving.py` produit directement un MusicXML percussion à deux voix, avec rendu MuseScore et grille estimée depuis l’audio. Les limites musicales sont décrites dans `docs/notation.md`.
- MuseScore Studio 4.7.5.260831071 : installé sous `work/tools/MuseScore 4.app`, sans installation globale ; export PDF réel testé. DMG officiel et SHA-256 figés dans `configs/musescore.json`. Le CLI disponible utilise `-o`, sans ancien drapeau `-s`. Abort natif intermittent observé : verrou de rendu et au plus trois tentatives pour SIGABRT ; autres erreurs immédiates, journaux conservés. Export XML vers MIDI natif non validé ; les MIDI livrés viennent du quantificateur.
- ADTOF Plus : pas installé ; étape ultérieure si les diagnostics le justifient.
- Verovio 6.3.0 : rendu SVG des vues privées de validation, installé uniquement
  dans `.venv` ; option `review` épinglée dans `pyproject.toml`. Les projections
  des références restent distinctes de la chaîne de transcription. Poppler
  fournit les images des PDF ; aucun document n'est envoyé à un service externe.

## Licences et poids
ADTOF original : [CC BY-NC-SA 4.0](https://github.com/MZehren/ADTOF/blob/master/LICENSE).
Le port [ADTOF-pytorch](https://github.com/xavriley/ADTOF-pytorch) n'a pas de LICENSE séparée dans le commit consulté ; sa déclaration de licence et celle des poids convertis ne sont pas explicites. Conserver la provenance de l'original et cette incertitude ; aucune publication ni redistribution des poids. Les poids du port sont inclus localement.
Demucs : code MIT ; le [dépôt](https://github.com/adefossez/demucs) annonce une licence MIT générale, sans déclaration séparée des poids vérifiée ici. Poids officiels téléchargés et hash intégral vérifié ; aucun texte de licence des poids distinct du dépôt trouvé. Usage local privé, aucune redistribution.
DrumScript : Apache-2.0 d'après pyproject.toml et LICENSE ; pas de nouveau poids appris propre détecté dans la baseline déterministe, séparation héritée de Demucs.
All-In-One : code [MIT](https://github.com/mir-aidj/all-in-one/blob/main/LICENSE) ; les poids externes n'ont pas été téléchargés ou audités. Leur licence doit être vérifiée avant utilisation.
Ces états séparent disponibilité du code, disponibilité des poids et validation de l'inférence.
