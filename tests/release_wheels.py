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
from gi_stub_gen.wheel_index import validate_wheel, write_index


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
dependencies = {[] if name == "gi-base-stubs" else ["gi-base-stubs"]!r}
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
    releases, data = [], {}
    for ubuntu, glib, output in (("24.04", "2.80", old), ("26.04", "2.88", recent)):
        manifest_name = f"stub-build-glib{glib}.json"
        manifest = json.loads((output / manifest_name).read_text())
        manifest["images"] = [dict(ubuntu=ubuntu, image=manifest["environment"]["image"])]
        prefix = f"https://github.com/example/stubs/releases/download/glib-{glib}/"
        assets = {manifest_name: json.dumps(manifest).encode(),
                  **{path.name: path.read_bytes() for path in output.glob("*.whl")}}
        data.update({prefix + name: blob for name, blob in assets.items()})
        releases.append(dict(tag_name=f"glib-{glib}", assets=[
            dict(name=name, browser_download_url=prefix + name) for name in assets
        ]))
    site = tmp_path / "site"
    write_index("example/stubs", releases, site, data.__getitem__)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(tmp_path)))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        # Serve validated release assets locally; the real index always links to GitHub.
        for page in site.rglob("index.html"):
            text = page.read_text()
            for glib in ("2.80", "2.88"):
                text = text.replace(f"https://github.com/example/stubs/releases/download/glib-{glib}/",
                                    f"{base_url}/wheels-{glib}/")
            page.write_text(text)
        env = tmp_path / "venv"
        subprocess.run(["uv", "venv", "--python", sys.executable, str(env)], check=True)
        python = str(env / "bin/python")
        url = f"{base_url}/site/simple/"
        for spec, expected in (("gi-base-stubs==3.58.1", "3.58.1+glib2.88"),
                               ("gi-base-stubs==3.58.1+glib2.80", "3.58.1+glib2.80")):
            subprocess.run(["uv", "pip", "install", "--python", python, "--no-deps", "--index-url", url, spec], check=True)
            result = subprocess.check_output([python, "-c", "from importlib.metadata import version; print(version('gi-base-stubs'))"], text=True)
            assert result.strip() == expected
        for ubuntu, glib in (("24.04", "2.80"), ("26.04", "2.88")):
            env = tmp_path / f"venv-{ubuntu}"
            subprocess.run(["uv", "venv", "--python", sys.executable, str(env)], check=True)
            python = str(env / "bin/python")
            url = f"{base_url}/site/ubuntu/{ubuntu}/simple/"
            subprocess.run(["uv", "pip", "install", "--python", python, "--index-url", url, "gi-gst-stubs"], check=True)
            result = subprocess.check_output([python, "-c", (
                "from importlib.metadata import version; "
                "print(version('gi-gst-stubs')); print(version('gi-base-stubs'))"
            )], text=True)
            assert result.splitlines() == [f"1.28.8+glib{glib}", f"3.58.1+glib{glib}"]
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
