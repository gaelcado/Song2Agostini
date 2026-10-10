"""Tests HTTP synthétiques : aucune inférence et aucune référence musicale."""
import http.client
import json
import threading
import time
from pathlib import Path

import pytest

from drum_lab.ui import Application, LocalServer, MAX_BYTES, summarize, validate_audio


def fake_generate(audio, out, **kwargs):
    kwargs["progress"](70, "Notation")
    paths = {}
    for kind, name in (("pdf", "score.pdf"), ("musicxml", "score.musicxml"), ("midi", "score.mid"), ("raw_midi", "raw.mid")):
        path = out / name
        path.write_bytes(b"synthetic artifact")
        paths[kind] = str(path)
    return {"status": "completed", "artifacts": paths, "warnings": ["Grille à vérifier."]}


@pytest.fixture
def local_server(tmp_path):
    instances = []
    def start(generate=fake_generate, validator=lambda path: None):
        app = Application(tmp_path / str(len(instances)), generate, validator)
        server = LocalServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        instances.append((server, app, thread))
        return server, app
    yield start
    for server, app, thread in instances:
        server.shutdown()
        server.server_close()
        app.close()
        thread.join(2)


def request(server, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    conn.request(method, path, body=body, headers=headers or {})
    response = conn.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    conn.close()
    return result


def session(server):
    status, headers, body = request(server, "GET", "/api/session")
    assert status == 200
    return {"Cookie": headers["Set-Cookie"].split(";")[0], "X-Session-Token": json.loads(body)["token"]}


def upload(server, headers, filename="test.wav"):
    status, _, body = request(server, "POST", "/api/jobs?filename=" + filename, b"fake audio", headers)
    assert status == 202, body
    return json.loads(body)["id"]


def completed(server, headers, job_id):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        status, _, body = request(server, "GET", "/api/jobs/" + job_id, headers=headers)
        assert status == 200
        data = json.loads(body)
        if data["status"] in {"completed", "failed"}:
            return data
        time.sleep(.01)
    pytest.fail("job non terminé")


def test_local_page_and_complete_download_flow(local_server):
    server, app = local_server()
    status, headers, body = request(server, "GET", "/")
    assert status == 200 and b"Song2Agostini" in body
    assert b"verification" not in body and b"Validation humaine" not in body
    assert "Content-Security-Policy" in headers
    auth = session(server)
    job = upload(server, auth)
    data = completed(server, auth, job)
    assert data["status"] == "completed" and data["percent"] == 100
    assert len(data["artifacts"]) == 4
    assert str(app.root).encode() not in json.dumps(data).encode()
    status, headers, body = request(server, "GET", data["artifacts"]["pdf"], headers=auth)
    assert status == 200 and body == b"synthetic artifact"
    assert headers["Content-Disposition"].startswith("inline")
    status, headers, _ = request(server, "GET", data["artifacts"]["pdf"] + "?download=1", headers=auth)
    assert status == 200 and headers["Content-Disposition"].startswith("attachment")


def test_job_details_are_numbers_without_paths_or_hashes(local_server, tmp_path):
    def generate(audio, out, **kwargs):
        (out / "notation").mkdir()
        (out / "notation" / "notation.json").write_text(json.dumps({
            "measures": 78, "displayed_measures": 40, "input_hits": 1162,
            "notation_chord_hits": 1147, "duplicate_notation_hits_collapsed": 15,
            "quality": {"median_shift_ms": 7.26, "max_shift_ms": 31.4, "large_shift_count": 0},
            "outputs": {"score.pdf": "/private/secret/score.pdf"}, "renderer_sha256": "abc"}))
        (out / "grid.json").write_text(json.dumps({"bpm": 90.9, "time_signature": "4/4", "duration_seconds": 217.9}))
        return fake_generate(audio, out, **kwargs) | {"duration_seconds": 321.4}
    server, _ = local_server(generate)
    auth = session(server)
    data = completed(server, auth, upload(server, auth))
    assert data["details"] == {
        "audio_seconds": 217.9, "tempo_bpm": 90.9, "time_signature": "4/4", "measures": 78,
        "displayed_measures": 40, "detected_hits": 1162, "engraved_hits": 1147, "merged_hits": 15,
        "median_shift_ms": 7.3, "max_shift_ms": 31.4, "large_shifts": 0, "compute_seconds": 321}
    assert "secret" not in json.dumps(data) and "abc" not in json.dumps(data)


def test_summary_tolerates_missing_or_malformed_files(tmp_path):
    assert summarize(tmp_path, {}) == {}
    (tmp_path / "grid.json").write_text("[1, 2")
    assert summarize(tmp_path, {"event_count": 12, "duration_seconds": float("nan")}) == {"detected_hits": 12}


def test_host_origin_token_and_session_isolation(local_server):
    server, _ = local_server()
    auth = session(server)
    assert request(server, "GET", "/", headers={"Host": "evil.example"})[0] == 403
    assert request(server, "GET", "/api/session", headers={"Origin": "https://evil.example"})[0] == 403
    assert request(server, "POST", "/api/jobs?filename=x.wav", b"x", {"Cookie": auth["Cookie"]})[0] == 403
    assert request(server, "POST", "/api/jobs?filename=x.wav", b"x", auth | {"Origin": "https://evil.example"})[0] == 403
    job = upload(server, auth)
    other = session(server)
    assert request(server, "GET", "/api/jobs/" + job, headers=other)[0] == 404
    assert request(server, "GET", "/api/jobs/" + job)[0] == 404


def test_input_limits_and_path_traversal(local_server):
    server, _ = local_server()
    auth = session(server)
    for filename in ("..%2Fsecret.wav", "..%5Csecret.wav", "audio.pdf"):
        assert request(server, "POST", "/api/jobs?filename=" + filename, b"x", auth)[0] == 400
    assert request(server, "POST", "/api/jobs?filename=x.wav", b"", auth)[0] == 413
    assert request(server, "POST", "/api/jobs?filename=x.wav", b"", auth | {"Content-Length": str(MAX_BYTES + 1)})[0] == 413
    for path in ("/data/raw/scores/x.pdf", "/../AGENTS.md", "/%2e%2e/AGENTS.md", "/api/jobs/../input"):
        assert request(server, "GET", path, headers=auth)[0] == 404


def test_engine_runs_serially_and_queue_is_bounded(local_server):
    gate = threading.Event()
    entered = threading.Event()
    active = 0
    maximum = 0
    calls = 0
    lock = threading.Lock()
    def slow(audio, out, **kwargs):
        nonlocal active, maximum, calls
        with lock:
            active += 1
            maximum = max(maximum, active)
            calls += 1
        entered.set()
        gate.wait(3)
        result = fake_generate(audio, out, **kwargs)
        with lock:
            active -= 1
        return result
    server, _ = local_server(slow)
    auth = session(server)
    jobs = [upload(server, auth)]
    assert entered.wait(2)
    jobs.extend([upload(server, auth), upload(server, auth)])
    assert request(server, "POST", "/api/jobs?filename=x.wav", b"x", auth)[0] == 429
    gate.set()
    for job in jobs:
        assert completed(server, auth, job)["status"] == "completed"
    assert maximum == 1 and calls == 3


def test_artifact_escape_is_rejected_and_error_is_private(local_server, tmp_path):
    external = tmp_path / "private.txt"
    external.write_text("private synthetic data")
    def escaped(audio, out, **kwargs):
        return {"status": "completed", "artifacts": {"pdf": str(external), "musicxml": str(external)}}
    server, app = local_server(escaped)
    auth = session(server)
    job = upload(server, auth)
    data = completed(server, auth, job)
    assert data["status"] == "failed"
    assert data["artifacts"] == {}
    assert "private" not in data["error"]
    assert (app.root / job / "error.log").is_file()
    assert request(server, "GET", "/api/jobs/" + job + "/error.log", headers=auth)[0] == 404


def test_invalid_duration_prevents_inference(local_server):
    called = False
    def engine(*args, **kwargs):
        nonlocal called
        called = True
    def invalid(path):
        raise ValueError("secret diagnostic")
    server, _ = local_server(engine, invalid)
    auth = session(server)
    data = completed(server, auth, upload(server, auth))
    assert data["status"] == "failed" and not called
    assert "secret diagnostic" not in json.dumps(data)


@pytest.mark.parametrize("duration", ["1801", "0", "NaN"])
def test_ffprobe_duration_limits(tmp_path, monkeypatch, duration):
    import drum_lab.ui as module
    monkeypatch.setattr(module.shutil, "which", lambda name: "/ffprobe")
    class Result:
        stdout = json.dumps({"format": {"duration": duration}, "streams": [{"codec_type": "audio"}]})
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: Result())
    with pytest.raises(ValueError):
        validate_audio(tmp_path / "input.wav")


def test_server_cannot_bind_network(local_server, tmp_path):
    app = Application(tmp_path, fake_generate, lambda p: None)
    with pytest.raises(ValueError):
        LocalServer(("0.0.0.0", 0), app)
    app.close()


def test_preview_is_cached_and_session_confined(local_server, monkeypatch):
    import drum_lab.ui as module
    calls = []
    def preview(pdf, output):
        calls.append(pdf)
        target = output / "preview-page-1.png"
        target.write_bytes(b"synthetic PNG")
        return target
    monkeypatch.setattr(module, "render_preview", preview)
    server, _ = local_server()
    auth = session(server)
    data = completed(server, auth, upload(server, auth))
    assert "preview" not in data["artifacts"]
    assert request(server, "GET", data["preview"], headers=session(server))[0] == 404
    for _ in range(2):
        status, headers, body = request(server, "GET", data["preview"], headers=auth)
        assert status == 200 and headers["Content-Type"] == "image/png"
        assert body == b"synthetic PNG"
    assert len(calls) == 1


def test_preview_failure_does_not_remove_downloads(local_server, monkeypatch):
    import drum_lab.ui as module
    def failed(*args):
        raise RuntimeError("private renderer failure")
    monkeypatch.setattr(module, "render_preview", failed)
    server, app = local_server()
    auth = session(server)
    job = upload(server, auth)
    data = completed(server, auth, job)
    status, _, body = request(server, "GET", data["preview"], headers=auth)
    assert status == 404 and b"private" not in body
    assert request(server, "GET", data["artifacts"]["pdf"], headers=auth)[0] == 200
    assert (app.root / job / "preview-error.log").is_file()


def test_preview_renders_only_first_page_locally(tmp_path, monkeypatch):
    import drum_lab.ui as module
    monkeypatch.setattr(module.shutil, "which", lambda name: "/local/pdftoppm")
    pdf = tmp_path / "partition.pdf"
    pdf.write_bytes(b"synthetic PDF")
    def run(command, **kwargs):
        assert command[:5] == ["/local/pdftoppm", "-f", "1", "-l", "1"]
        assert "-singlefile" in command and kwargs["check"]
        assert "shell" not in kwargs
        Path(command[-1] + ".png").write_bytes(b"PNG")
    monkeypatch.setattr(module.subprocess, "run", run)
    assert module.render_preview(pdf, tmp_path).read_bytes() == b"PNG"


def test_product_uses_audio_downbeats_without_reference(local_server):
    calls = []
    def engine(audio, output, **kwargs):
        calls.append(kwargs)
        return fake_generate(audio, output, **kwargs)
    server, _ = local_server(engine)
    auth = session(server)
    data = completed(server, auth, upload(server, auth, "morceau.wav"))
    assert data["status"] == "completed"
    assert len(calls) == 1
    assert calls[0]["config"] == {"separate_drums": True, "compact": True, "grid_engine": "beat_this"}
    assert calls[0]["piece_id"] == "piece_01" and calls[0]["title"] == "morceau"
    assert data["warnings"] == ["Grille à vérifier."]
    for url in data["artifacts"].values():
        assert request(server, "GET", url, headers=auth)[0] == 200


def test_product_assets_have_no_review_navigation_or_api(local_server):
    server, _ = local_server()
    for path in ("/", "/app.js", "/style.css"):
        status, _, body = request(server, "GET", path)
        assert status == 200
        assert b"/verification" not in body
        assert b"Validation humaine" not in body
