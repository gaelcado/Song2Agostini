'use strict';
const byId = id => document.getElementById(id);
let selectedFile = null;
let token = null;
let busy = false;
let currentJob = null;
let pollTimer = null;

function showError(message) {
  byId('error').textContent = message;
  byId('error').hidden = false;
}
function selectFile(file) {
  if (busy || !file) return;
  byId('error').hidden = true;
  if (!/\.(wav|flac|mp3)$/i.test(file.name) || !file.size || file.size > 200 * 1024 * 1024) {
    selectedFile = null;
    byId('generate').disabled = true;
    showError('Choisissez un fichier WAV, FLAC ou MP3 non vide, de 200 Mo maximum.');
    return;
  }
  selectedFile = file;
  const stem = file.name.replace(/\.(wav|flac|mp3)$/i, '');
  byId('file-label').textContent = /^(piece|bench|tech)_\d+$/i.test(stem) ? 'Audio sélectionné' : stem;
  byId('file-detail').textContent = `${(file.size / 1024 / 1024).toLocaleString('fr-FR', {maximumFractionDigits: 1})} Mo · Cliquez pour changer`;
  byId('generate').disabled = !token;
}
function progress(percent, label) {
  byId('progress-section').hidden = false;
  byId('progress').value = percent;
  byId('percent').textContent = `${percent} %`;
  byId('progress-label').textContent = label;
}
function release() {
  busy = false;
  byId('audio').disabled = false;
  byId('generate').disabled = !selectedFile || !token;
  byId('generate').textContent = 'Générer une nouvelle partition →';
}
function renderResult(data) {
  byId('empty').hidden = true;
  byId('result').hidden = false;
  byId('draft-badge').hidden = false;
  const downloads = byId('downloads');
  downloads.replaceChildren();
  const labels = {pdf: 'Télécharger le PDF ↓', musicxml: 'MusicXML ↓', midi: 'MIDI quantifié ↓', raw_midi: 'MIDI brut ↓'};
  for (const kind of ['pdf', 'musicxml', 'midi', 'raw_midi']) {
    if (!data.artifacts[kind]) continue;
    const link = document.createElement('a');
    link.href = data.artifacts[kind] + '?download=1';
    link.textContent = labels[kind];
    link.setAttribute('download', '');
    downloads.append(link);
  }
  byId('open-pdf').href = data.artifacts.pdf;
  byId('pdf-preview').hidden = false;
  byId('preview-unavailable').hidden = true;
  byId('pdf-preview').src = data.preview;
  byId('warning-list').replaceChildren();
  const warnings = ['Grille issue de l’audio : brouillon à vérifier à l’écoute.', ...data.warnings];
  for (const warning of [...new Set(warnings)]) {
    const item = document.createElement('li');
    const readableWarnings = {
      'Déplacements supérieurs à 50 ms : grille à vérifier': 'Certaines notes ont été déplacées pour suivre la grille. Vérifiez leur rythme à l’écoute.',
      'Collisions même instrument : regroupées dans la notation uniquement': 'Des coups rapprochés du même instrument partagent une note dans la partition. Le MIDI brut les conserve.',
      'Pistes mélodiques ignorées : seule la batterie est gravée': 'La partition contient uniquement la batterie.',
      'La fidélité musicale n’est pas validée automatiquement face à une référence humaine.': 'Certaines notes peuvent être manquantes ou ajoutées. Écoutez le morceau en suivant la partition.',
      'Premiers temps prédits par un modèle audio expérimental ; brouillon non validé.': 'Les débuts de mesure sont estimés depuis l’audio. Une entrée avant le premier temps ou un changement de rythme peut demander une correction.',
    };
    item.textContent = warning.startsWith('MusicXML relatif')
      ? 'La partition commence à la première pulsation estimée ; le MIDI brut conserve la position dans l’audio.'
      : (readableWarnings[warning] || warning);
    byId('warning-list').append(item);
  }
  byId('warnings').hidden = false;
  byId('progress-note').textContent = 'Le PDF est prêt. Le MusicXML permet de modifier la partition.';
}
byId('pdf-preview').addEventListener('error', () => {
  byId('pdf-preview').hidden = true;
  byId('preview-unavailable').hidden = false;
});
async function poll() {
  try {
    const response = await fetch(`/api/jobs/${currentJob}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Traitement indisponible.');
    if (data.title) {
      byId('file-label').textContent = data.title;
      byId('output-title').textContent = data.title;
    }
    progress(data.percent, data.status === 'queued' ? 'En attente du moteur local' : data.label);
    if (data.status === 'completed') {
      renderResult(data);
      sessionStorage.removeItem('drum-job');
      release();
    } else if (data.status === 'failed') {
      showError(data.error);
      byId('progress-note').textContent = 'Traitement arrêté. Vous pouvez choisir un autre audio et réessayer.';
      sessionStorage.removeItem('drum-job');
      release();
    } else {
      pollTimer = setTimeout(poll, 1400);
    }
  } catch (error) {
    showError(error.message || 'Connexion locale interrompue. Rechargez la page pour reprendre le suivi.');
    release();
  }
}
byId('audio').addEventListener('change', event => selectFile(event.target.files[0]));
const zone = byId('dropzone');
for (const name of ['dragenter', 'dragover']) zone.addEventListener(name, event => {event.preventDefault(); if (!busy) zone.classList.add('drag');});
for (const name of ['dragleave', 'drop']) zone.addEventListener(name, event => {event.preventDefault(); zone.classList.remove('drag');});
zone.addEventListener('drop', event => selectFile(event.dataTransfer.files[0]));
byId('generate').addEventListener('click', () => {
  if (!selectedFile || !token || busy) return;
  clearTimeout(pollTimer);
  busy = true;
  byId('audio').disabled = true;
  byId('generate').disabled = true;
  byId('error').hidden = true;
  byId('progress-note').textContent = 'Le calcul local peut prendre plusieurs minutes.';
  progress(0, 'Copie de l’audio dans l’atelier');
  const request = new XMLHttpRequest();
  request.open('POST', `/api/jobs?filename=${encodeURIComponent(selectedFile.name)}`);
  request.setRequestHeader('Content-Type', 'application/octet-stream');
  request.setRequestHeader('X-Session-Token', token);
  request.upload.onprogress = event => { if (event.lengthComputable) progress(0, `Copie de l’audio · ${Math.round(event.loaded / event.total * 100)} %`); };
  request.onload = () => {
    try {
      const data = JSON.parse(request.responseText);
      if (request.status !== 202) throw new Error(data.error || 'Transfert impossible.');
      byId('file-label').textContent = data.title;
      byId('output-title').textContent = data.title;
      currentJob = data.id;
      sessionStorage.setItem('drum-job', currentJob);
      poll();
    } catch (error) { showError(error.message); release(); }
  };
  request.onerror = () => {showError('Connexion locale interrompue pendant le transfert.'); release();};
  request.send(selectedFile);
});
(async () => {
  try {
    const response = await fetch('/api/session');
    if (!response.ok) throw new Error('Session locale indisponible.');
    token = (await response.json()).token;
    currentJob = sessionStorage.getItem('drum-job');
    if (currentJob) { busy = true; byId('audio').disabled = true; poll(); }
    else byId('generate').disabled = !selectedFile;
  } catch (error) {showError(error.message);}
})();
