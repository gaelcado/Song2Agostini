"""Freeze existing isolated engine environments, never the global interpreter."""
import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINES = {"adtof": ["adtof_pytorch", "torch", "librosa", "pretty_midi"],
           "demucs": ["demucs", "torch", "torchaudio", "soundfile", "einops", "numpy"],
           "beat_this": ["beat_this", "torch", "torchaudio", "librosa", "einops"]}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, default=ROOT / "work")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--engine", choices=list(ENGINES), action="append")
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    for engine in args.engine or ENGINES:
        python = args.runtime_root / "envs" / engine / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        if not python.is_file():
            raise FileNotFoundError(python)
        subprocess.run(["uv", "pip", "install", "--python", str(python), "pyinstaller==6.16.0",
                        "pyinstaller-hooks-contrib==2026.8", "backports.tarfile==1.2.0"], check=True)
        build = ROOT / "work" / "worker-build" / engine
        build.mkdir(parents=True, exist_ok=True)
        command = [str(python), "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
                   "--console", "--name", engine, "--distpath", str(args.output.resolve()),
                   "--workpath", str(build / "objects"), "--specpath", str(build),
                   "--exclude-module", "PySide6", "--exclude-module", "PyQt5", "--exclude-module", "tensorflow"]
        for package in [*ENGINES[engine], "backports.tarfile"]:
            command.extend(["--collect-all", package])
        if engine == "demucs":
            # Official old checkpoints pickle NumPy 1 module names, including under NumPy 2.
            command.extend(["--hidden-import", "numpy.core.multiarray",
                            "--hidden-import", "numpy.core._multiarray_umath"])
        command.append(str(ROOT / "packaging" / "worker_entry.py"))
        subprocess.run(command, cwd=ROOT, check=True)
        executable = args.output / engine / (engine + (".exe" if sys.platform == "win32" else ""))
        module = ENGINES[engine][0]
        subprocess.run([str(executable), "-c", f"import {module}; print('worker import OK: {engine}')"], check=True)
        (args.output / engine / "build.json").write_text(json.dumps({"platform": sys.platform,
            "architecture": platform.machine(), "engine": engine, "command": command}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
