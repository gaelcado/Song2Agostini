'use strict';
const byId = id => document.getElementById(id);
const AUDIO = /\.(wav|flac|mp3)$/i;
const MAX_BYTES = 200 * 1024 * 1024;
// Les seuils reprennent les jalons de progression du moteur (pipeline.generate).
const STEPS = [
  {from: -1, name: 'Copie locale', why: 'Le fichier est copié dans un dossier de travail de cet ordinateur. Il n’est envoyé nulle part.'},
  {from: 0, name: 'Lecture de l’audio', why: 'Vérifie que le fichier est un audio lisible de 30 minutes maximum.'},
  {from: 10, name: 'Isolation de la batterie', why: 'Un modèle exécuté ici sépare la batterie du reste du morceau. C’est l’étape la plus longue.'},
  {from: 52, name: 'Détection des coups', why: 'Repère chaque coup (grosse caisse, caisse claire, charleston, toms, cymbales) et son instant exact.'},
  {from: 68, name: 'Pulsation', why: 'Estime le tempo et les premiers temps à partir du morceau complet, pas de la batterie seule.'},
  {from: 80, name: 'Mise en page', why: 'Cale chaque coup sur une grille de doubles croches puis compose la partition.'},
  {from: 94, name: 'Contrôle des fichiers', why: 'Contrôle la cohérence du PDF, du MusicXML et des fichiers MIDI avant de les proposer.'},
];
const FILES = {
  pdf: ['Partition PDF', 'Toutes les pages, à lire ou à imprimer'],
  musicxml: ['MusicXML', 'Pour modifier la partition dans un éditeur'],
  midi: ['MIDI quantifié', 'Coups calés sur la grille de la partition'],
  raw_midi: ['MIDI brut', 'Instants exacts des coups dans l’audio'],
};
const READABLE_WARNINGS = {
  'Déplacements supérieurs à 50 ms : grille à vérifier': 'Certaines notes ont été déplacées pour suivre la grille. Vérifiez leur rythme à l’écoute.',
  'Collisions même instrument : regroupées dans la notation uniquement': 'Des coups rapprochés du même instrument partagent une note dans la partition. Le MIDI brut les conserve.',
  'Pistes mélodiques ignorées : seule la batterie est gravée': 'La partition contient uniquement la batterie.',
  'La fidélité musicale n’est pas validée automatiquement face à une référence humaine.': 'Certaines notes peuvent être manquantes ou ajoutées. Écoutez le morceau en suivant la partition.',
  'Premiers temps prédits par un modèle audio expérimental ; brouillon non validé.': 'Les débuts de mesure sont estimés depuis l’audio. Une entrée avant le premier temps ou un changement de rythme peut demander une correction.',
};
let selectedFile = null;
let token = null;
let busy = false;
let uploading = false;
let currentJob = null;
let pollTimer = null;
let clock = null;
let startedAt = 0;

const number = (value, digits = 0) => value.toLocaleString('fr-FR', {maximumFractionDigits: digits});
function setView(view) { document.body.dataset.view = view; }
function showError(message) {
  byId('error').textContent = message;
  byId('error').hidden = false;
}

function buildWaves() {
  for (const wave of document.querySelectorAll('.wave')) {
    for (let i = 0; i < 32; i++) {
      const bar = document.createElement('i');
      bar.style.setProperty('--h', `${Math.round(16 + 70 * Math.abs(Math.sin(i * 0.9) * Math.cos(i * 0.37 + 1)))}%`);
      bar.style.setProperty('--i', i);
      wave.append(bar);
    }
  }
}
function stepItem(step) {
  const item = document.createElement('li');
  const name = document.createElement('b');
  name.textContent = step.name;
  const why = document.createElement('small');
  why.textContent = step.why;
  item.append(name, why);
  return item;
}
function buildSteps() {
  for (const step of STEPS) byId('steps').append(stepItem(step));
  for (const step of STEPS) {
    const item = stepItem(step);
    item.dataset.state = 'done';
    byId('recap').append(item);
  }
}
function stageFor(percent) {
  if (uploading) return 0;
  let index = 1;
  for (let i = 1; i < STEPS.length; i++) if (percent >= STEPS[i].from) index = i;
  return index;
}
function showSteps(active) {
  [...byId('steps').children].forEach((item, index) => {
    item.dataset.state = index < active ? 'done' : index === active ? 'active' : 'todo';
  });
}

function selectFile(file) {
  if (busy || !file) return;
  byId('error').hidden = true;
  if (!AUDIO.test(file.name) || !file.size || file.size > MAX_BYTES) {
    selectedFile = null;
    byId('generate').disabled = true;
    byId('dropzone').classList.remove('has-file');
    showError('Choisissez un fichier WAV, FLAC ou MP3 non vide, de 200 Mo maximum.');
    return;
  }
  selectedFile = file;
  const stem = file.name.replace(AUDIO, '');
  byId('file-label').textContent = /^(piece|bench|tech)_\d+$/i.test(stem) ? 'Audio sélectionné' : stem;
  byId('file-detail').textContent = `${number(file.size / 1024 / 1024, 1)} Mo · cliquez pour changer`;
  byId('dropzone').classList.add('has-file');
  byId('generate-label').textContent = 'Générer la partition';
  byId('generate').disabled = !token;
  setView('idle');
}
function tick() {
  const seconds = Math.max(0, Math.round((Date.now() - startedAt) / 1000));
  byId('elapsed').textContent = `Calcul sur cet ordinateur · ${Math.floor(seconds / 60)} min ${String(seconds % 60).padStart(2, '0')} s`;
}
function startClock() {
  clearInterval(clock);
  startedAt = Date.now();
  tick();
  clock = setInterval(tick, 1000);
}
function progress(percent, label) {
  byId('progress').value = percent;
  byId('percent').textContent = `${percent} %`;
  byId('progress-label').textContent = label;
  showSteps(stageFor(percent));
}
function release() {
  busy = false;
  uploading = false;
  clearInterval(clock);
  byId('audio').disabled = false;
  byId('generate').disabled = !selectedFile || !token;
}
function fail(message, forget = true) {
  showError(message);
  if (forget) sessionStorage.removeItem('drum-job');
  release();
  setView('idle');
}

function fact(label, value, hint) {
  const row = document.createElement('div');
  const term = document.createElement('dt');
  term.textContent = label;
  const detail = document.createElement('dd');
  detail.append(value);
  if (hint) {
    const small = document.createElement('small');
    small.textContent = hint;
    detail.append(small);
  }
  row.append(term, detail);
  byId('facts').append(row);
}
function renderFacts(details) {
  byId('facts').replaceChildren();
  const d = details || {};
  if (d.audio_seconds != null) {
    const total = Math.round(d.audio_seconds);
    fact('Durée', `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`, 'Durée de l’audio analysé.');
  }
  if (d.tempo_bpm != null) fact('Tempo', `≈ ${number(d.tempo_bpm)} BPM${d.tempo_unit ? ` · ${d.tempo_unit}` : ''}`, 'Estimé depuis l’audio : à confronter à votre oreille.');
  if (d.time_signature) fact('Mesure', d.time_signature, d.meter_status === 'candidate'
    ? 'Candidate issue de l’audio ; premiers temps et changements locaux à vérifier.'
    : d.meter_status === 'incertain' ? 'Regroupement incertain : notation provisoire à vérifier.'
    : 'Hypothèse de grille historique, à vérifier.');
  if (d.measures != null) {
    const folded = d.displayed_measures != null && d.displayed_measures < d.measures;
    fact('Mesures', number(d.measures), folded
      ? `${number(d.displayed_measures)} écrites ; les passages identiques sont regroupés en reprises.`
      : 'Toutes les mesures sont écrites.');
  }
  if (d.engraved_hits != null) {
    const parts = [];
    if (d.detected_hits != null) parts.push(`${number(d.detected_hits)} coups détectés`);
    if (d.merged_hits) parts.push(`${number(d.merged_hits)} partagent une note (le MIDI brut les conserve)`);
    parts.push('les coups manqués ne sont pas comptés');
    fact('Notes', number(d.engraved_hits), parts.join(' · ') + '.');
  }
  if (d.median_shift_ms != null && d.max_shift_ms != null) {
    const far = d.large_shifts ? `${number(d.large_shifts)} dépassent 50 ms : à vérifier.` : 'Aucun décalage notable.';
    fact('Calage', `${number(d.median_shift_ms)} ms · max ${number(d.max_shift_ms)} ms`, `Écart entre chaque coup et sa case dans la grille. ${far}`);
  }
}
function renderResult(data) {
  const downloads = byId('downloads');
  downloads.replaceChildren();
  for (const kind of Object.keys(FILES)) {
    if (kind === 'pdf' || !data.artifacts[kind]) continue;
    const link = document.createElement('a');
    link.href = data.artifacts[kind] + '?download=1';
    link.setAttribute('download', '');
    const [name, hint] = FILES[kind];
    const small = document.createElement('small');
    small.textContent = hint;
    link.append(name, small);
    downloads.append(link);
  }
  byId('open-pdf').href = data.artifacts.pdf;
  byId('download-pdf').href = data.artifacts.pdf + '?download=1';
  byId('pdf-preview').src = data.artifacts.pdf + '#view=FitH';
  byId('editor-status').hidden = true;
  byId('open-musescore').disabled = false;
  renderFacts(data.details);
  const warnings = ['Grille issue de l’audio : brouillon à vérifier à l’écoute.', ...data.warnings];
  const list = byId('warning-list');
  list.replaceChildren();
  for (const warning of new Set(warnings)) {
    const item = document.createElement('li');
    item.textContent = warning.startsWith('MusicXML relatif')
      ? 'La partition commence à la première pulsation estimée ; le MIDI brut conserve la position dans l’audio.'
      : (READABLE_WARNINGS[warning] || warning);
    list.append(item);
  }
  const seconds = data.details && data.details.compute_seconds;
  byId('compute-note').textContent = seconds != null
    ? `Tout a été calculé sur cet ordinateur en ${Math.floor(seconds / 60)} min ${String(Math.round(seconds % 60)).padStart(2, '0')} s.`
    : 'Tout a été calculé sur cet ordinateur.';
  setView('done');
}
byId('open-musescore').addEventListener('click', async () => {
  const button = byId('open-musescore');
  const status = byId('editor-status');
  button.disabled = true;
  status.hidden = false;
  status.textContent = 'Ouverture dans MuseScore…';
  try {
    const response = await fetch(`/api/jobs/${currentJob}/open-musescore`, {
      method: 'POST', headers: {'X-Session-Token': token},
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Ouverture impossible.');
    status.textContent = 'La partition a été transmise à MuseScore.';
  } catch (error) {
    status.textContent = error.message || 'Impossible de joindre l’application locale.';
  } finally {
    button.disabled = false;
  }
});

function setTitle(title) {
  if (!title) return;
  byId('file-label').textContent = title;
  byId('run-title').textContent = title;
  byId('output-title').textContent = title;
}
async function poll() {
  try {
    const response = await fetch(`/api/jobs/${currentJob}`);
    const data = await response.json();
    if (!response.ok) {
      const gone = new Error(data.error || 'Traitement indisponible.');
      gone.gone = response.status === 404;
      throw gone;
    }
    setTitle(data.title);
    progress(data.percent, data.status === 'queued' ? 'En attente du moteur local' : data.label);
    if (data.status === 'completed') {
      renderResult(data);
      sessionStorage.removeItem('drum-job');
      release();
    } else if (data.status === 'failed') {
      byId('generate-label').textContent = 'Réessayer';
      fail(data.error);
    } else {
      pollTimer = setTimeout(poll, 1400);
    }
  } catch (error) {
    fail(error.message || 'Connexion locale interrompue. Rechargez la page pour reprendre le suivi.', Boolean(error.gone));
  }
}
function generate() {
  if (!selectedFile || !token || busy) return;
  clearTimeout(pollTimer);
  busy = true;
  uploading = true;
  byId('audio').disabled = true;
  byId('generate').disabled = true;
  byId('error').hidden = true;
  setTitle(byId('file-label').textContent);
  startClock();
  setView('run');
  progress(0, 'Copie de l’audio');
  const request = new XMLHttpRequest();
  request.open('POST', `/api/jobs?filename=${encodeURIComponent(selectedFile.name)}`);
  request.setRequestHeader('Content-Type', 'application/octet-stream');
  request.setRequestHeader('X-Session-Token', token);
  request.upload.onprogress = event => {
    if (event.lengthComputable) progress(0, `Copie de l’audio · ${Math.round(event.loaded / event.total * 100)} %`);
  };
  request.onload = () => {
    try {
      const data = JSON.parse(request.responseText);
      if (request.status !== 202) throw new Error(data.error || 'Transfert impossible.');
      uploading = false;
      setTitle(data.title);
      currentJob = data.id;
      sessionStorage.setItem('drum-job', currentJob);
      poll();
    } catch (error) { fail(error.message, false); }
  };
  request.onerror = () => fail('Connexion locale interrompue pendant le transfert.', false);
  request.send(selectedFile);
}

byId('audio').addEventListener('change', event => {
  selectFile(event.target.files[0]);
  event.target.value = '';
});
byId('generate').addEventListener('click', generate);
byId('again').addEventListener('click', () => {
  byId('error').hidden = true;
  setView('idle');
  byId('audio').click();
});
document.addEventListener('keydown', event => {
  if (event.key === 'Enter' && document.body.dataset.view === 'idle' && !byId('generate').disabled
      && !event.target.closest('button, a')) {
    event.preventDefault();
    generate();
  }
});
// Dépôt accepté n’importe où dans la fenêtre.
let depth = 0;
const hasFiles = event => [...(event.dataTransfer?.types || [])].includes('Files');
window.addEventListener('dragenter', event => {
  if (!busy && hasFiles(event)) { depth++; document.body.classList.add('dragging'); }
});
window.addEventListener('dragleave', () => {
  depth = Math.max(0, depth - 1);
  if (!depth) document.body.classList.remove('dragging');
});
window.addEventListener('dragover', event => event.preventDefault());
window.addEventListener('drop', event => {
  event.preventDefault();
  depth = 0;
  document.body.classList.remove('dragging');
  if (!busy && hasFiles(event)) selectFile(event.dataTransfer.files[0]);
});

buildWaves();
buildSteps();
(async () => {
  try {
    const response = await fetch('/api/session');
    if (!response.ok) throw new Error('Session locale indisponible.');
    token = (await response.json()).token;
    currentJob = sessionStorage.getItem('drum-job');
    if (currentJob) {
      busy = true;
      byId('audio').disabled = true;
      startClock();
      setView('run');
      poll();
    } else byId('generate').disabled = !selectedFile;
  } catch (error) { showError(error.message); }
})();
