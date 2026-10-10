# Composants tiers et limites de distribution

La licence MIT du dépôt couvre le code propre à Song2Agostini. Elle ne remplace pas les licences des dépendances, modèles, données ou outils tiers. Aucun poids, enregistrement ou partition de référence n’est publié ici.

| Composant | Usage | Déclaration amont et état |
|---|---|---|
| [ADTOF-pytorch](https://github.com/xavriley/ADTOF-pytorch) | Détection des coups | Commit `85c192e78f716ea0b111cc8a5ee4a8f6a3a4f8a9` : pas de fichier LICENSE ni autorisation explicite pour le port. Redistribution du port et de son bundle **non approuvée**. |
| [ADTOF original](https://github.com/MZehren/ADTOF/blob/master/LICENSE) | Origine du modèle | CC BY-NC-SA 4.0 ; restriction non commerciale. Cela ne fournit pas automatiquement une licence aux ajouts du port PyTorch. |
| [Demucs](https://github.com/adefossez/demucs/blob/main/LICENSE) | Isolation de batterie | Code MIT. Les poids sont fournis par le projet ; aucune déclaration distincte des poids n’a été identifiée dans l’audit local. Garder cette distinction pour une distribution. |
| [Beat This](https://github.com/CPJKU/beat_this#license) | Temps et premiers temps | MIT annoncé pour code et poids. |
| [MuseScore 4.6.5](https://github.com/MuseScore/MuseScore/blob/v4.6.5/LICENSE.txt) / [4.7.5](https://github.com/MuseScore/MuseScore/blob/v4.7.5/LICENSE.txt) | Export PDF (Mac : 4.6.5 ; validation Windows : 4.7.5) | GPL-3.0 ; garder les notices et respecter les obligations de distribution et d’accès aux sources correspondantes. |
| [Qt for Python / PySide6](https://doc.qt.io/qtforpython-6/licenses.html) | Fenêtre native | LGPLv3/GPLv3 ou licence commerciale selon composants. QtWebEngine inclut aussi des dépendances tierces. |
| [FFmpeg](https://ffmpeg.org/legal.html) | Lecture et conversion audio | LGPL ou GPL selon la configuration du binaire. Vérifier chaque build embarqué, garder notices et sources correspondantes. |

Les versions installables et commits sont figés dans `configs/install/`. Le bootstrap consigne les métadonnées de licence déclarées par chaque distribution Python dans `runtime-install.json`. Ces déclarations ne constituent pas à elles seules une autorisation de redistribution.

L’installation depuis les sources télécharge les composants directement depuis leurs sources amont pour une utilisation locale. Cela ne garantit pas les droits pour tout usage commercial. La publication d’un `.exe` ou `.dmg` contenant l’ensemble du moteur reste bloquée tant que les droits du port ADTOF et les obligations des composants embarqués ne sont pas résolus. Un prototype local privé peut être construit pour vérifier son fonctionnement ; il ne constitue pas une release publique autorisée.

Les scripts de construction conservent un manifeste de composants, hashes, notices et informations de sources. `redistribution_approved=false` doit rester explicite pour les bundles actuels.
