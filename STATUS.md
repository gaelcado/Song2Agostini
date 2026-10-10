# Où en est Song2Agostini ?

L’application produit un PDF de batterie, un MusicXML et des MIDI. Le calcul reste local et une fenêtre native est disponible depuis les sources.

**La sortie reste un brouillon.** La fidélité musicale n’a pas encore de pourcentage validé : les partitions humaines doivent être numérisées et leur alignement vérifié indépendamment.

L’installation neuve et l’application Mac autonome ont été vérifiées : un morceau réel a produit PDF, MusicXML et MIDI sans utiliser les outils du projet. Les 190 tests passent sur Mac, Linux et Windows Server 2022/2025. Le PDF et les trois moteurs ont été exécutés sur Windows Server 2022 ; WSL1 Ubuntu 24.04 a aussi passé les tests et exporté un PDF. Windows 10/11 et WSL2 restent à vérifier. Les paquets complets publics sont bloqués par les droits de redistribution du moteur ADTOF utilisé.

Pour commencer : [INSTALL.md](INSTALL.md). Pour les preuves techniques : [état du laboratoire](docs/STATUS.md) et [compatibilité](docs/platform-support.md).
