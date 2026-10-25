"""Explicit packaging integration: backend metadata, real installation and immutability."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import subprocess
import sys
from threading import Thread
import zipfile

import pytest

from gi_stub_gen.release import PACKAGES, build_release
from gi_stub_gen.wheel_index import validate_wheel


def test_release_wheels_and_installer_selection(tmp_path):
    def build(glib, canonical):
        stubs = tmp_path / f"stubs-{glib}"
        for name in PACKAGES:
            project = stubs / name
            source = project / "src/gi-stubs"
            source.mkdir(parents=True)
            (source / "__init__.pyi").write_text("value: int\n")
            public = "1.28.8" if name == "gi-gst-stubs" else "3.58.1"
            (project / "pyproject.toml").write_text(f'''
[project]
name = "{name}"
version = "{public}+glib{glib}"
requires-python = ">=3.12"
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
[tool.hatch.build.targets.wheel]
packages = ["src/gi-stubs"]
''')
        output = tmp_path / f"wheels-{glib}"
        native = dict(image="image@sha256:" + "a" * 64, glib=glib, gtk="4.22", gstreamer="1.28.8", python="3.14")
        manifest = build_release(stubs, output, native, canonical=canonical)
        with pytest.raises(FileExistsError):
            build_release(stubs, output, native)
        for entry in json.loads(manifest.read_text())["wheels"]:
            validate_wheel(entry, (output / entry["filename"]).read_bytes())
        return output

    old, recent = build("2.80", False), build("2.88", True)
    native = recent / "gi_base_stubs-3.58.1+glib2.88-py3-none-any.whl"
    canonical = recent / "gi_base_stubs-3.58.1-py3-none-any.whl"
    with zipfile.ZipFile(native) as a, zipfile.ZipFile(canonical) as b:
        assert {p: a.read(p) for p in a.namelist() if p.startswith("gi-stubs/")} == {
            p: b.read(p) for p in b.namelist() if p.startswith("gi-stubs/")
        }
    index = tmp_path / "simple/gi-base-stubs"
    index.mkdir(parents=True)
    wheels = [*old.glob("gi_base_stubs-*.whl"), *recent.glob("gi_base_stubs-*.whl")]
    (index / "index.html").write_text("\n".join(
        f'<a href="../../{p.parent.name}/{p.name}">{p.name}</a>' for p in wheels
    ))
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(tmp_path)))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        env = tmp_path / "venv"
        subprocess.run(["uv", "venv", "--python", sys.executable, str(env)], check=True)
        python = str(env / "bin/python")
        url = f"http://127.0.0.1:{server.server_port}/simple/"
        for spec, expected in (("gi-base-stubs==3.58.1", "3.58.1+glib2.88"),
                               ("gi-base-stubs==3.58.1+glib2.80", "3.58.1+glib2.80")):
            subprocess.run(["uv", "pip", "install", "--python", python, "--no-deps", "--index-url", url, spec], check=True)
            result = subprocess.check_output([python, "-c", "from importlib.metadata import version; print(version('gi-base-stubs'))"], text=True)
            assert result.strip() == expected
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
