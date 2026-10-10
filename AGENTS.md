# Song2Agostini — consignes aux agents

Le produit est une petite application pour musiciens : choisir un audio, générer une partition de batterie, consulter le PDF et télécharger PDF/MusicXML/MIDI. Communiquer en français simplement.

- Pour installer, lire INSTALL.md puis docs/installation-technique.md. Utiliser Python 3.11 dans des environnements isolés ; ne pas modifier Python global.
- Préserver les originaux, références et résultats locaux. Ne pas envoyer d’audio à un service externe.
- Les références manuelles sont exclusivement destinées au vérificateur, jamais au moteur de transcription ni à ses exemples. Appliquer docs/separation.md.
- La partition principale est le PDF multipage, accompagné du MusicXML éditable. Ne pas présenter un brouillon ou une grille non validée comme une partition fidèle garantie.
- Pour toute recherche ou évaluation, lire lab/AGENTS.md et docs/STATUS.md. Les sous-agents de recherche et vérification utilisent des contextes distincts sans historique partagé.
- Vérifier les changements utiles, mettre à jour l’état et distinguer tests logiciels, jugement musical et plateformes effectivement testées.
- Le dépôt public contient le code propre au projet. Ne pas publier données privées, poids ou binaires tiers sans droits de redistribution établis ; consulter THIRD_PARTY_NOTICES.md.
