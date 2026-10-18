"""Explicit integration suite: run with `just test-installed-stubs` after generation."""

import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("gi-base-stubs", "gi-graphics-core-stubs", "gi-gst-stubs", "gi-gtk-stubs")


def stub_hashes(directory: Path) -> dict[str, str]:
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.rglob("*") if path.is_file()
    }


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=180)


def checked(*args: str) -> str:
    result = run(*args)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


@pytest.fixture(scope="module")
def installed(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path, list[Path]]:
    work = tmp_path_factory.mktemp("installed-stubs")
    wheels = work / "wheels"
    for package in PACKAGES:
        checked("uv", "build", "--wheel", str(ROOT / "stubs" / package), "--out-dir", str(wheels))
    archives = sorted(wheels.glob("*.whl"))
    assert len(archives) == len(PACKAGES)

    owners: dict[str, str] = {}
    for archive in archives:
        with zipfile.ZipFile(archive) as wheel:
            record = next(name for name in wheel.namelist() if name.endswith(".dist-info/RECORD"))
            for name, _, _ in csv.reader(io.StringIO(wheel.read(record).decode())):
                assert name not in owners, f"Overlapping wheel file: {name}"
                owners[name] = archive.name
    for marker in ("gi-stubs/py.typed", "gi-stubs/repository/__init__.pyi", "gi-stubs/_gi.pyi", "gi-stubs/events.pyi", "gi-stubs/_signalhelper.pyi"):
        assert owners[marker].startswith("gi_base_stubs-")

    assert owners["gi-stubs/_gtktemplate.pyi"].startswith("gi_gtk_stubs-")

    env = work / "venv"
    checked("uv", "venv", "--python", sys.executable, str(env))
    python = env / "bin/python"
    site = Path(checked(str(python), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))").strip())
    # Copy runtime bindings only, never installed stubs that could hide broken wheels.
    for module in ("gi", "cairo", "typing_extensions"):
        spec = importlib.util.find_spec(module)
        assert spec is not None and spec.origin is not None
        source = Path(spec.origin)
        if spec.submodule_search_locations is not None:
            shutil.copytree(source.parent, site / module)
        else:
            shutil.copy2(source, site / source.name)
    (site / "gi/repository/RuntimeProbe.py").write_text("def answer() -> int:\n    return 42\n")
    checked("uv", "pip", "install", "--python", str(python), "--no-deps", *map(str, reversed(archives)))
    return work, site, archives


@pytest.mark.parametrize("checker", ["pyright", "ty-check"])
def test_installed_consumers(installed: tuple[Path, Path, list[Path]], checker: str):
    work, _, _ = installed
    python = str(work / "venv/bin/python")
    for fixture in ("consumer", "invalid", "parity", "parity_invalid", "gstreamer_typed_pipeline", "namespaces"):
        source = work / f"{fixture}.py"
        if fixture == "namespaces":
            names = sorted({path.stem for path in (ROOT / "stubs").glob("*/src/gi-stubs/repository/*.pyi") if path.stem != "__init__"})
            source.write_text("from typing import assert_type\n" + "\n".join(
                f"from gi.repository import {name}\nassert_type({name}.__name__, str)" for name in names
            ))
        else:
            original = ROOT / "examples/gstreamer_typed_pipeline.py" if fixture == "gstreamer_typed_pipeline" else ROOT / "tests/typing" / f"{fixture}.py.txt"
            source.write_text(original.read_text())
        expected = [number for number, line in enumerate(source.read_text().splitlines(), 1) if "# error" in line and not (checker == "ty-check" and "ty-misses:" in line)]
        if checker == "pyright":
            result = run("just", checker, "--pythonpath", python, "--outputjson", str(source))
            diagnostics = json.loads(result.stdout)["generalDiagnostics"]
            assert all(item["severity"] == "error" and Path(item["file"]) == source for item in diagnostics)
            actual = [item["range"]["start"]["line"] + 1 for item in diagnostics]
        else:
            result = run("just", checker, "--python", python, "--output-format", "gitlab", str(source))
            diagnostics = json.loads(result.stdout)
            assert all(item["severity"] == "major" and Path(item["location"]["path"]) == source for item in diagnostics)
            actual = [item["location"]["positions"]["begin"]["line"] for item in diagnostics]
        # A rejected constructor can produce separate __new__ and __init__ diagnostics.
        assert sorted(set(actual)) == expected, result.stdout + result.stderr
        assert result.returncode == (1 if expected else 0), result.stdout + result.stderr


def test_addon_removal_preserves_other_packages(installed: tuple[Path, Path, list[Path]]):
    work, site, archives = installed
    python = str(work / "venv/bin/python")
    stub_dir = site / "gi-stubs"
    before = stub_hashes(stub_dir)
    gst = next(archive for archive in archives if archive.name.startswith("gi_gst_stubs-"))
    with zipfile.ZipFile(gst) as wheel:
        gst_files = {name.removeprefix("gi-stubs/") for name in wheel.namelist() if name.startswith("gi-stubs/")}
    checked("uv", "pip", "uninstall", "--python", python, "gi-gst-stubs")
    after = stub_hashes(stub_dir)
    assert after == {name: value for name, value in before.items() if name not in gst_files}
    checked("uv", "pip", "install", "--python", python, "--no-deps", str(gst))
    assert stub_hashes(stub_dir) == before
    assert (stub_dir / "py.typed").read_text() == "partial\n"
