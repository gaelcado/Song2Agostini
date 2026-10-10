"""Interface locale : aucun accès HTTP aux références ou aux chemins arbitraires."""
from __future__ import annotations

import json
import math
import queue
import secrets
import shutil
import subprocess
import threading
import time
import traceback
import uuid
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit, quote
from .titles import audio_title
from .files import find_tool
from .processes import run_external

MAX_BYTES = 200 * 1024 * 1024
MAX_DURATION = 30 * 60
REJECT_DRAIN_BYTES = 64 * 1024
REJECT_DRAIN_SECONDS = .250
WEB = Path(__file__).with_name("web")
ARTIFACT_TYPES = {
    "pdf": ("application/pdf", "partition.pdf"),
    "musicxml": ("application/vnd.recordare.musicxml+xml", "partition.musicxml"),
    "midi": ("audio/midi", "partition.mid"),
    "raw_midi": ("audio/midi", "placement-brut.mid"),
}


def validate_audio(path: Path) -> None:
    """Vérifie le contenu et borne sa durée avant toute inférence."""
    ffprobe = find_tool("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe indisponible")
    result = run_external(
        [ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type",
         "-of", "json", str(path)], capture_output=True, text=True, timeout=30,
        check=True,
    )
    metadata = json.loads(result.stdout)
    duration = float(metadata["format"]["duration"])
    if not math.isfinite(duration) or not 0 < duration <= MAX_DURATION:
        raise ValueError("durée audio invalide")
    if not any(stream.get("codec_type") == "audio" for stream in metadata.get("streams", [])):
        raise ValueError("aucun flux audio")


def _generate(*args, **kwargs):
    from drum_lab.pipeline import generate
    return generate(*args, **kwargs)


def render_preview(pdf: Path, output: Path) -> Path:
    """Rend uniquement la première page avec l'outil local Poppler."""
    executable = find_tool("pdftoppm")
    if not executable:
        # Native desktop ships QtPdf, so no external Poppler runtime is needed.
        from PySide6.QtCore import QSize
        from PySide6.QtPdf import QPdfDocument
        document = QPdfDocument()
        if document.load(str(pdf)) != QPdfDocument.Error.None_ or document.pageCount() < 1:
            raise RuntimeError("PDF illisible")
        size = document.pagePointSize(0)
        scale = 1400 / max(size.width(), size.height())
        preview = output / "preview-page-1.png"
        rendered = document.render(0, QSize(round(size.width() * scale), round(size.height() * scale)))
        if rendered.isNull() or not rendered.save(str(preview)):
            raise RuntimeError("aperçu manquant")
        document.close()
        return preview
    prefix = output / "preview-page-1"
    run_external([executable, "-f", "1", "-l", "1", "-scale-to", "1400",
                    "-png", "-singlefile", str(pdf), str(prefix)],
                   check=True, capture_output=True, timeout=60)
    preview = prefix.with_suffix(".png")
    if not preview.is_file() or not preview.resolve().is_relative_to(output.resolve()):
        raise RuntimeError("aperçu manquant")
    return preview


def summarize(output: Path, result: dict) -> dict:
    """Chiffres lisibles du calcul pour l'interface ; ni chemin ni empreinte."""
    def load(name):
        try:
            value = json.loads((output / name).read_text())
        except (OSError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}

    def number(value, digits=1):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return None
        return round(value, digits)

    notation, grid = load("notation/notation.json"), load("grid.json")
    quality = notation.get("quality") if isinstance(notation.get("quality"), dict) else {}
    signature = grid.get("time_signature")
    pulse_length = grid.get("pulse_quarter_length", 1)
    tempo = number(grid.get("bpm"))
    if pulse_length == 1.5 and tempo is not None:
        tempo = number(grid["bpm"] / 1.5)
    fields = {
        "audio_seconds": number(grid.get("duration_seconds", result.get("audio_duration_seconds"))),
        "tempo_bpm": tempo,
        "time_signature": signature if isinstance(signature, str) and len(signature) <= 5 else None,
        "measures": number(notation.get("measures"), 0),
        "displayed_measures": number(notation.get("displayed_measures"), 0),
        "detected_hits": number(notation.get("input_hits", result.get("event_count")), 0),
        "engraved_hits": number(notation.get("notation_chord_hits"), 0),
        "merged_hits": number(notation.get("duplicate_notation_hits_collapsed"), 0),
        "median_shift_ms": number(quality.get("median_shift_ms")),
        "max_shift_ms": number(quality.get("max_shift_ms")),
        "large_shifts": number(quality.get("large_shift_count"), 0),
        "compute_seconds": number(result.get("duration_seconds"), 0),
    }
    evidence = grid.get("meter_evidence")
    if isinstance(evidence, dict):
        fields["tempo_unit"] = "noire pointée" if pulse_length == 1.5 else "noire"
        fields["meter_status"] = "candidate" if evidence.get("status") == "inferred_hypothesis" else "incertain"
    return {key: value for key, value in fields.items() if value is not None}


class Application:
    def __init__(self, root: Path, generate=None, validator=None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.generate = generate or _generate
        self.validator = validator or validate_audio
        self.sessions: set[str] = set()
        self.jobs: dict[str, dict] = {}
        self.lock = threading.RLock()
        self.pending = queue.Queue()
        self.worker = threading.Thread(target=self._work, daemon=True)
        self.worker.start()

    def _work(self):
        while True:
            job_id = self.pending.get()
            if job_id is None:
                self.pending.task_done()
                return
            job = self.jobs[job_id]
            try:
                self._progress(job_id, 2, "Vérification de l’audio")
                self.validator(job["input"])
                result = self.generate(
                    job["input"], job["output"],
                    config={"separate_drums": True, "compact": True, "grid_engine": "beat_this"},
                    piece_id="piece_01", title=job["title"],
                    progress=lambda percent, label: self._progress(job_id, percent, label),
                )
                if result.get("status") != "completed":
                    raise RuntimeError("génération incomplète")
                artifacts = {}
                for kind, value in result.get("artifacts", {}).items():
                    if kind not in ARTIFACT_TYPES or not value:
                        continue
                    path = Path(value).resolve()
                    if path.is_relative_to(job["output"].resolve()) and path.is_file():
                        artifacts[kind] = path
                if "pdf" not in artifacts or "musicxml" not in artifacts:
                    raise RuntimeError("sorties de notation manquantes")
                with self.lock:
                    job.update(status="completed", percent=100, label="Partition prête",
                               artifacts=artifacts, details=summarize(job["output"], result),
                               warnings=[str(w)[:1000] for w in result.get("warnings", [])])
            except Exception:
                (job["input"].parent / "error.log").write_text(traceback.format_exc())
                with self.lock:
                    job.update(status="failed", label="La génération n’a pas abouti.",
                               error="Vérifiez que l’audio est lisible (30 minutes maximum) et que les outils locaux sont installés. Les détails sont conservés dans le journal local du traitement.")
            finally:
                self.pending.task_done()

    def _progress(self, job_id, percent, label):
        with self.lock:
            job = self.jobs[job_id]
            job.update(status="running", percent=max(job["percent"], min(99, max(0, int(percent)))),
                       label=str(label)[:250])

    def close(self):
        self.pending.put(None)


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, app):
        if address[0] != "127.0.0.1":
            raise ValueError("Le serveur doit écouter uniquement sur 127.0.0.1")
        self.app = app
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Ne journalise ni noms de fichiers ni jetons de session.

    def _security(self):
        port = self.server.server_port
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        host = self.headers.get("Host", "")
        if host not in hosts:
            self._json(403, {"error": "Accès local uniquement."})
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in {"http://" + h for h in hosts}:
            self._json(403, {"error": "Origine non autorisée."})
            return False
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            self._json(403, {"error": "Origine non autorisée."})
            return False
        return True

    def _session(self):
        try:
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            token = cookie["drum_session"].value if "drum_session" in cookie else ""
        except Exception:
            return None
        return token if token in self.server.app.sessions else None

    def _drain_rejected_body(self):
        # Closing an unread small POST may reset TCP and hide its HTTP refusal on Windows.
        if not getattr(self, '_post_body_unread', False):
            return
        self._post_body_unread = False
        lengths = self.headers.get_all('Content-Length', [])
        if len(lengths) != 1 or 'Transfer-Encoding' in self.headers:
            return
        try:
            remaining = int(lengths[0])
        except ValueError:
            return
        if not 0 < remaining <= REJECT_DRAIN_BYTES:
            return
        previous_timeout = self.connection.gettimeout()
        deadline = time.monotonic() + REJECT_DRAIN_SECONDS
        try:
            while remaining:
                budget = deadline - time.monotonic()
                if budget <= 0:
                    break
                self.connection.settimeout(budget)
                # read1 performs at most one underlying read; slow drips cannot renew the budget.
                chunk = self.rfile.read1(min(4096, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
        except OSError:
            pass  # Still send the same HTTP refusal; never admit an invalid request.
        finally:
            self.connection.settimeout(previous_timeout)

    def _send(self, status, data, mime, extra=None):
        if self.command == 'POST' and status >= 400:
            self._drain_rejected_body()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; frame-src 'self'; object-src 'self'; base-uri 'none'; frame-ancestors 'self'")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, status, value, extra=None):
        self._send(status, json.dumps(value, ensure_ascii=False).encode(), "application/json; charset=utf-8", extra)

    def do_GET(self):
        if not self._security():
            return
        path = urlsplit(self.path).path
        if path in {"/", "/app.js", "/style.css"}:
            name, mime = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}[path]
            self._send(200, (WEB / name).read_bytes(), mime + "; charset=utf-8")
            return
        if path == "/api/session":
            with self.server.app.lock:
                token = self._session() or secrets.token_urlsafe(32)
                self.server.app.sessions.add(token)
            self._json(200, {"token": token}, {"Set-Cookie": f"drum_session={token}; HttpOnly; SameSite=Strict; Path=/"})
            return
        session = self._session()
        parts = path.strip("/").split("/")
        if not session or len(parts) not in {3, 4} or parts[:2] != ["api", "jobs"]:
            self._json(404, {"error": "Ressource introuvable."})
            return
        with self.server.app.lock:
            job = self.server.app.jobs.get(parts[2])
            if not job or job["session"] != session:
                self._json(404, {"error": "Traitement introuvable."})
                return
            if len(parts) == 3:
                self._json(200, {key: job[key] for key in ("id", "title", "status", "percent", "label", "warnings", "error", "details")} | {
                    "artifacts": {kind: f"/api/jobs/{job['id']}/{kind}" for kind in job["artifacts"]},
                    "preview": f"/api/jobs/{job['id']}/preview" if "pdf" in job["artifacts"] else None,
                })
                return
            kind = parts[3]
            if kind == "preview":
                if "pdf" not in job["artifacts"]:
                    self._json(404, {"error": "Aperçu indisponible."})
                    return
                try:
                    if not job["artifacts"]["pdf"].resolve().is_relative_to(job["output"].resolve()):
                        raise ValueError("PDF hors traitement")
                    preview = job.get("preview")
                    if preview is None:
                        preview = render_preview(job["artifacts"]["pdf"], job["output"])
                        job["preview"] = preview
                    if not preview.resolve().is_relative_to(job["output"].resolve()):
                        raise ValueError("aperçu hors traitement")
                    self._send(200, preview.read_bytes(), "image/png")
                except Exception:
                    (job["input"].parent / "preview-error.log").write_text(traceback.format_exc())
                    self._json(404, {"error": "Aperçu indisponible. Ouvrez ou téléchargez le PDF."})
                return
            artifact = job["artifacts"].get(kind)
            if kind not in ARTIFACT_TYPES or artifact is None or not artifact.resolve().is_relative_to(job["output"].resolve()):
                self._json(404, {"error": "Fichier indisponible."})
                return
            mime, name = ARTIFACT_TYPES[kind]
            attachment = parse_qs(urlsplit(self.path).query).get("download") == ["1"]
            titled_name = job["title"].replace("/", "-").replace("\\", "-") + " - " + name
            disposition = f'{"attachment" if attachment or kind != "pdf" else "inline"}; filename="{name}"; filename*=UTF-8\'\'{quote(titled_name, safe="")}'
            self._send(200, artifact.read_bytes(), mime, {"Content-Disposition": disposition})

    def do_POST(self):
        self._post_body_unread = True
        self.connection.settimeout(60)
        if not self._security():
            return
        session = self._session()
        if not session or not secrets.compare_digest(self.headers.get("X-Session-Token", ""), session):
            self._json(403, {"error": "Session invalide. Rechargez la page."})
            return
        parsed = urlsplit(self.path)
        if parsed.path != "/api/jobs":
            self._json(404, {"error": "Ressource introuvable."})
            return
        filename = parse_qs(parsed.query).get("filename", [""])[0]
        suffix = Path(filename).suffix.lower()
        if suffix not in {".wav", ".flac", ".mp3"} or len(filename) > 250 or "/" in filename or "\\" in filename:
            self._json(400, {"error": "Choisissez un fichier WAV, FLAC ou MP3."})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            size = 0
        if self.headers.get("Transfer-Encoding") or not 0 < size <= MAX_BYTES:
            self._json(413, {"error": "Fichier vide ou supérieur à 200 Mo."})
            return
        app = self.server.app
        with app.lock:
            if sum(j["status"] in {"uploading", "queued", "running"} for j in app.jobs.values()) >= 3:
                self._json(429, {"error": "Trois traitements sont déjà en cours. Réessayez ensuite."})
                return
            job_id = uuid.uuid4().hex
            directory = app.root / job_id
            directory.mkdir()
            output = directory / "output"
            output.mkdir()
            job = dict(id=job_id, session=session, status="uploading", percent=0,
                       label="En attente", warnings=[], error=None, artifacts={}, details={},
                       input=directory / ("input" + suffix), output=output,
                       title=Path(filename).stem[:120])
            app.jobs[job_id] = job
        try:
            self._post_body_unread = False
            remaining = size
            with job["input"].open("wb") as stream:
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("upload interrompu")
                    stream.write(chunk)
                    remaining -= len(chunk)
        except Exception:
            with app.lock:
                app.jobs.pop(job_id, None)
            shutil.rmtree(directory)
            self._json(400, {"error": "Transfert interrompu. Réessayez."})
            return
        with app.lock:
            job["title"] = audio_title(job["input"], filename)
            job["status"] = "queued"
            app.pending.put(job_id)
        self._json(202, {"id": job_id, "title": job["title"]})


def serve(port: int = 8765):
    app = Application(Path("work/ui/jobs"))
    server = LocalServer(("127.0.0.1", port), app)
    print(f"Interface locale : http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        app.close()
