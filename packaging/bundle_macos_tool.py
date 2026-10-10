"""Copy a Mach-O CLI and absolute non-system dylibs, then relocate and sign."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


def dependencies(path):
    lines = subprocess.check_output(["otool", "-L", str(path)], text=True).splitlines()[1:]
    return [line.strip().split(" (", 1)[0] for line in lines]


def bundle(source, output):
    source = source.resolve()
    output.mkdir(parents=True, exist_ok=True)
    libs = output / "lib"
    libs.mkdir(exist_ok=True)
    mapping = {}
    relations = {}

    def visit(original, destination):
        original = original.resolve()
        if original in mapping:
            return
        if destination.exists() and destination.read_bytes() != original.read_bytes():
            # Already-relocated binaries legitimately differ on repeated runs.
            raise ValueError(f"Destination déjà présente : {destination}. Utiliser un dossier vide.")
        shutil.copy2(original, destination)
        destination.chmod(destination.stat().st_mode | 0o200)
        mapping[original] = destination
        relations[original] = []
        for dependency in dependencies(original):
            if dependency.startswith(("/System/", "/usr/lib/")):
                continue
            if dependency.startswith("@"):
                raise ValueError(f"Dépendance rpath à résoudre explicitement : {original} : {dependency}")
            resolved = Path(dependency).resolve()
            if resolved == original:
                continue  # dylib's own install ID
            if not resolved.is_file():
                raise FileNotFoundError(resolved)
            relations[original].append((dependency, resolved))
            visit(resolved, libs / resolved.name)

    visit(source, output / source.name)
    for original, destination in mapping.items():
        subprocess.run(["codesign", "--remove-signature", str(destination)], capture_output=True)
        if destination.parent == libs:
            subprocess.run(["install_name_tool", "-id", "@loader_path/" + destination.name, str(destination)], check=True)
        for dependency, resolved in relations[original]:
            prefix = "@loader_path/" if destination.parent == libs else "@executable_path/lib/"
            subprocess.run(["install_name_tool", "-change", dependency,
                            prefix + mapping[resolved].name, str(destination)], check=True)
        subprocess.run(["codesign", "--force", "--sign", "-", str(destination)], check=True, capture_output=True)
    return {str(destination.relative_to(output)): hashlib.sha256(destination.read_bytes()).hexdigest()
            for destination in mapping.values()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("macOS uniquement")
    result = bundle(args.source, args.output)
    (args.output / (args.source.name + "-bundle.json")).write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
