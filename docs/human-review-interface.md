# Vérification privée depuis le chat

La validation humaine est retirée de l’application livrée, conformément au
[handoff produit](handoff-produit-et-simplification.md). L’application propose
uniquement audio → génération → aperçu PDF et téléchargements. `/verification`,
ses assets et tous les accès `/api/verification` sont indisponibles, y compris
avec une session locale valide. Aucune décision privée ne peut être enregistrée
par le serveur produit.

Les originaux, candidates, rendus et versions de décisions sous
`work/verification/` sont conservés. `human_review.py` reste un outil local pour
les preuves privées, sans lien avec le serveur de génération. Les scripts de
préparation et de rendu restent utilisables par le vérificateur : ils ne rendent
pas les documents accessibles par HTTP.

Les vérifications, passages ambigus et confirmations se présentent désormais
dans le chat, avec des fichiers locaux lisibles (PDF, images, audio ou rapport
ciblé). Le vérificateur conserve les références et les erreurs détaillées ; la
recherche reçoit uniquement les audios, paramètres et feedback agrégé. Appliquer
[la séparation des rôles](separation.md). La séparation reste logique sur le
disque partagé ; elle ne constitue pas un sandbox OS.

Les décisions déjà enregistrées gardent leur périmètre et leurs hashes. Leur
existence ne certifie ni une couverture complète ni un alignement valide. Aucune
confirmation supplémentaire n’est déduite du retrait de l’interface.

La description de l’ancien parcours est conservée dans
[l’archive historique](archive/human-review-interface-2026-10-10.md).
