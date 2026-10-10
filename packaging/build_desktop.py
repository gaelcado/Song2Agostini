"""Native builds only. Preview bundles UI; full release requires audited payload."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def link_or_copy(source, destination):
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)
    return destination


def verify_payload(path):
    """No relocated venv may be advertised as a standalone distribution."""
    manifest = json.loads((path / "distribution-manifest.json").read_text())
    if manifest.get("platform") != sys.platform or manifest.get("architecture") != platform.machine():
        raise ValueError("Runtime destiné à une autre plateforme/architecture")
    if manifest.get("self_contained") is not True:
        raise ValueError("Le manifeste ne certifie pas un runtime autonome")
    required = {"adtof", "demucs", "beat_this", "ffmpeg", "ffprobe", "musescore"}
    entries = manifest.get("components", {})
    if not required <= entries.keys():
        raise ValueError("Workers, ffmpeg/ffprobe ou MuseScore manquants")
    if (path / "envs").exists():
        raise ValueError("Les venv locaux ne sont pas des runtimes distribuables")
    for name, entry in entries.items():
        for field in ("path", "license_path", "source_offer_path"):
            target = (path / entry[field]).resolve()
            if not target.is_relative_to(path.resolve()) or not target.exists():
                raise ValueError(f"{name}: {field} absent ou hors runtime")
        for relative, expected in entry.get("sha256", {}).items():
            target = (path / relative).resolve()
            if not target.is_relative_to(path.resolve()) or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                raise ValueError(f"{name}: hash invalide {relative}")
        if not entry.get("sha256"):
            raise ValueError(f"{name}: aucun fichier vérifié")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preview", action="store_true", help="UI uniquement ; moteurs non embarqués")
    mode.add_argument("--runtime-payload", type=Path, help="runtime autonome vérifié pour cette plateforme")
    parser.add_argument("--dmg", action="store_true")
    args = parser.parse_args(argv)
    if sys.platform not in {"darwin", "win32"}:
        parser.error("Construire sur macOS ou Windows natif")
    payload_manifest = verify_payload(args.runtime_payload.resolve()) if args.runtime_payload else None
    name = "Song2AgostiniPreview" if args.preview else "Song2Agostini"
    build = ROOT / "work" / "desktop-build"
    build.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
               "--onedir", "--name", name, "--distpath", str(ROOT / "dist"),
               "--workpath", str(build / "objects"), "--specpath", str(build),
               "--paths", str(ROOT / "src"), "--collect-data", "drum_lab",
               "--hidden-import", "drum_lab.pipeline", "--hidden-import", "PySide6.QtWebEngineWidgets"]
    for directory in ("configs", "scripts", "src"):
        command.extend(["--add-data", f"{ROOT / directory}:source/{directory}"])
    # Frozen workers and MuseScore already own independent library trees.
    # Passing them as --add-data makes PyInstaller rewrite nested Mach-O paths
    # and mix their Qt libraries into the desktop's Qt runtime.
    if sys.platform == "darwin":
        command.extend(["--osx-bundle-identifier", "org.drumlab.song2agostini"])
    command.append(str(ROOT / "packaging" / "desktop_entry.py"))
    subprocess.run(command, cwd=ROOT, check=True)
    if args.runtime_payload:
        if sys.platform == "darwin":
            app_bundle = ROOT / "dist" / f"{name}.app"
            runtime_destination = app_bundle / "Contents" / "Resources" / "runtime"
        else:
            runtime_destination = ROOT / "dist" / name / "_internal" / "runtime"
        shutil.copytree(args.runtime_payload.resolve(), runtime_destination, symlinks=True)
        if sys.platform == "darwin":
            (app_bundle / "Contents" / "Frameworks" / "runtime").symlink_to("../Resources/runtime")
            subprocess.run(["codesign", "--force", "--sign", "-", str(app_bundle)], check=True)
    if sys.platform == "darwin":
        # BUNDLE already contains COLLECT; retain only the app to bound disk use.
        collected = ROOT / "dist" / name
        if collected.is_dir() and (ROOT / "dist" / f"{name}.app").is_dir():
            shutil.rmtree(collected)
    evidence = {"schema_version": 1, "name": name, "platform": sys.platform,
                "architecture": platform.machine(),
                "self_contained_inference": bool(payload_manifest and payload_manifest.get("offline_smoke_test_passed")),
                "runtime_included": bool(payload_manifest),
                "offline_smoke_test_passed": bool(payload_manifest and payload_manifest.get("offline_smoke_test_passed")),
                "redistribution_approved": bool(payload_manifest and payload_manifest.get("redistribution_approved")),
                "preview": args.preview, "python": sys.version, "build_command": command,
                "runtime_manifest": payload_manifest}
    (ROOT / "dist" / f"{name}-build.json").write_text(json.dumps(evidence, indent=2))
    if args.dmg:
        if sys.platform != "darwin":
            parser.error("--dmg requiert macOS")
        stage = build / "dmg-stage"
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir()
        # Same filesystem: hard links avoid a third full copy of heavy runtimes.
        shutil.copytree(ROOT / "dist" / f"{name}.app", stage / f"{name}.app",
                        symlinks=True, copy_function=link_or_copy)
        (stage / "Applications").symlink_to("/Applications")
        shutil.copy2(ROOT / "dist" / f"{name}-build.json", stage)
        explanation = ("Aperçu de l’interface : moteurs et modèles NON embarqués.\n"
                       "Cette image ne permet pas la transcription autonome d’un audio.\n") if args.preview else (
                       "Application privée avec runtime embarqué.\n"
                       "Vérification de génération hors ligne : " + ("réussie" if payload_manifest.get("offline_smoke_test_passed") else "à effectuer") + ".\n"
                       "Redistribution publique : " + ("autorisée par le manifeste" if payload_manifest.get("redistribution_approved") else "NON autorisée") + ".\n")
        (stage / "LISEZ-MOI.txt").write_text(explanation + "Build local non signé et non notarié.\n")
        dmg = ROOT / "dist" / f"{name}-macos-{platform.machine()}.dmg"
        subprocess.run(["hdiutil", "create", "-volname", name, "-srcfolder", str(stage),
                        "-ov", "-format", "UDZO", str(dmg)], check=True)
        shutil.rmtree(stage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
