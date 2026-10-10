# Essai de séparation locale kick / snare

Implémentation expérimentale indépendante des moteurs de transcription,
strictement audio. Source primaire des poids :
https://huggingface.co/Faridzar/timbrica-drum-separator/tree/3b3475f9b84c676d05441e38b16ed5deaa74d582
La carte du modèle décrit les tenseurs entrée/sortie et les données d'entraînement.
Les métriques annoncées par l'auteur ne sont pas des mesures sur notre morceau.

Poids kick et snare-r2 épinglés par commit et SHA256 dans `configs/kit-model.json`.
Licence des poids CC BY-NC-SA 4.0 ; licence du runtime ONNX Runtime MIT distincte.
Aucun code applicatif Timbrica copié, aucune souscription ni audio envoyé au service.
Runtime dans `work/envs/kit`, sans modification de Python global. Première version
ORT 1.23.2 indisponible pour Python 3.14 ; version locale 1.24.1 compatible installée
et verrouillée, y compris dépendances transitives.

Chaîne : batterie Demucs mise en cache → STFT stéréo (Hann périodique, FFT 4096,
hop 1024, centrage reflect) → magnitude non normalisée `[1,2,2048,512]` → masque
ONNX CPU → phase originale / ISTFT → ADTOF sur chaque stem. Seuls kick/snare
issus des stems correspondants sont conservés. Les trois autres classes viennent
de la détection originale sur batterie Demucs. Aucun accès à une référence.

Les masques sont appliqués indépendamment, sans redistribution Wiener ni modèle
toms ; cet essai ne reproduit donc pas la configuration complète annoncée par
l'auteur. Le bin Nyquist non prédit est mis à zéro. Les chunks temporels sont
contigus ; le dernier est complété par des zéros, dont les sorties sont supprimées.
Ces hypothèses, notamment le fenêtrage non détaillé par la carte publique,
restent une limite de cette adaptation. Waveforms FLOAT préservent le niveau
et ne sont pas normalisées ; diagnostics de clipping et masques `.npy` conservés.

Smoke : 20 premières secondes du stem piece_01 ; 3.14 s CPU (4 threads), deux
modèles, masques finis dans [0,1], aucun échantillon > 1. Le passage est faible
niveau (pic entrée 0.00481), ce contrôle prouve l'exécution et pas la qualité
musicale. Tests synthétiques : restitution STFT/ISTFT longueur/placement/tail,
padding temporel, audio invalide, intégrité poids et provenance audio, maintien
strict de la classe instrumentale de chaque stem. Cinq tests passent.

Une seule variante intégrale est autorisée, `configs/kit-detection-v4.json`,
seuils baseline inchangés, grille librosa audio inchangée. Les mesures de fidélité
appartiennent au vérificateur séparé. piece_02 reste réservé.

Exécution intégrale unique : `20261010T102825-8b369805`, statut
`awaiting_verification`, 55.58 s au total ; séparation du kit 36.02 s CPU pour
217.94 s d'audio. Cache du kit 440 Mo, incluant waveforms et deux masques
float32. Pics kick 0.92060 / snare 0.89959, aucun échantillon > 1, masques finis
sans valeurs hors [0,1]. 1 059 événements prédits (202 kick, 146 snare,
694 hi-hat, 8 toms, 9 cymbals). Ces comptages ne mesurent pas la fidélité.
Sorties PDF quatre pages (95 983 octets), MusicXML, MIDI brut et quantifié,
événements JSON et grille audio produits. Aucun second essai ni retry nécessaire.
Tests ciblés kit + pipeline : 24 passent. Le statut reste brouillon ; lisibilité,
fidélité et éventuelles observations auditives sont à vérifier séparément.
