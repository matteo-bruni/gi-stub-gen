"""Index tests also run in the Pages workflow without GI or project dependencies."""

import hashlib
import io
import json
import zipfile

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from gi_stub_gen.release import release_versions, validate_native_labels
from gi_stub_gen.wheel_index import validate_wheel, write_index


def wheel(version="3.58.1+glib2.88", name="gi-base-stubs", requirements="") -> tuple[dict, bytes]:
    stem = name.replace("-", "_")
    filename = f"{stem}-{version}-py3-none-any.whl"
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        prefix = f"{stem}-{version}.dist-info/"
        archive.writestr(prefix + "METADATA", f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\nRequires-Python: >=3.12\n{requirements}")
        archive.writestr(prefix + "WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
        archive.writestr("gi-stubs/__init__.pyi", "value: int\n")
        if name == "gi-stub-gen":
            archive.writestr(prefix + "entry_points.txt", "[console_scripts]\ngi-stub-gen = gi_stub_gen.cli.gi_stub_gen:app\n")
            archive.writestr("gi_stub_gen/templates/module.pyi.jinja", "template")
    data = target.getvalue()
    return dict(filename=filename, name=name, version=version, requires_python=">=3.12",
                canonical=Version(version).local is None, sha256=hashlib.sha256(data).hexdigest()), data


def release_assets(entries):
    prefix = "https://github.com/example/stubs/releases/download/v1/"
    native = dict(image="ghcr.io/example/image@sha256:" + "a" * 64, glib="2.88", gtk="4.22", gstreamer="1.28.8", python="3.14.9")
    manifest = json.dumps(dict(format_version=1, environment=native, wheels=[entry for entry, _ in entries])).encode()
    data = {prefix + "stub-build-glib2.88.json": manifest, **{prefix + entry["filename"]: blob for entry, blob in entries}}
    releases = [dict(tag_name="v1", draft=False, prerelease=False,
                     assets=[dict(name=url.rsplit("/", 1)[-1], browser_download_url=url) for url in data])]
    return releases, data


def test_versions_and_explicit_selection():
    versions = ["3.58.1", "3.58.1+glib2.80", "3.58.1+glib2.88"]
    assert sorted(versions, key=Version) == versions
    assert all(Version(value) in SpecifierSet("==3.58.1") for value in versions)
    assert list(SpecifierSet("==3.58.1+glib2.80").filter(versions)) == [versions[1]]
    assert release_versions("3.58.1+glib2.88", "2.88", True, 2) == ["3.58.1.post2+glib2.88", "3.58.1.post2"]
    assert release_versions("1.28.8", "2.80", False, None) == ["1.28.8+glib2.80"]
    with pytest.raises(ValueError, match="Malformed native label"):
        validate_native_labels("3.58.1+glib2.88.cairo", dict(glib="2.88", cairo="1.18"))


def test_static_index_and_catalog(tmp_path):
    releases, data = release_assets([wheel(), wheel("3.58.1")])
    output = tmp_path / "site"
    catalog = write_index("example/stubs", releases, output, data.__getitem__)
    assert len(catalog) == 2
    html = (output / "simple/gi-base-stubs/index.html").read_text()
    assert "#sha256=" in html and 'data-requires-python="&gt;=3.12"' in html
    assert "glib2.88" in html
    assert not list(output.rglob("*.whl"))
    assert (output / "catalog.json").exists()
    landing = (output / "index.html").read_text()
    assert "Install recommended wheels" in landing and "uv pip install" in landing
    assert "do not install runtime bindings" in landing and "do not detect GLib" in landing
    assert "catalog.json" in landing and 'href="simple/"' in landing
    command = landing.split("<pre><code>")[1].split("</code></pre>")[0]
    assert "gi_base_stubs-3.58.1-py3-none-any.whl#sha256=" in command
    assert "+glib" not in command
    with pytest.raises(ValueError, match="already exists"):
        write_index("example/stubs", releases, output, data.__getitem__)


@pytest.mark.parametrize("field,value", [("sha256", "bad"), ("version", "3.58.2"), ("requires_python", ">=3.14"), ("canonical", True)])
def test_rejects_manifest_mismatch(field, value):
    entry, data = wheel()
    entry[field] = value
    with pytest.raises(ValueError):
        validate_wheel(entry, data)


def test_rejects_discordant_duplicates(tmp_path):
    entry, blob = wheel()
    releases, data = release_assets([(entry, blob)])
    other = dict(releases[0], tag_name="v2")
    assets = releases[0]["assets"]
    assert isinstance(assets, list)
    other["assets"] = [dict(asset, browser_download_url=asset["browser_download_url"].replace("/v1/", "/v2/")) for asset in assets]
    for url, value in list(data.items()):
        if url.endswith(".whl"):
            value += b"different archive bytes"
        else:
            manifest = json.loads(value)
            manifest["wheels"][0]["sha256"] = hashlib.sha256(blob + b"different archive bytes").hexdigest()
            value = json.dumps(manifest).encode()
        data[url.replace("/v1/", "/v2/")] = value
    with pytest.raises(ValueError, match="Conflicting wheel"):
        write_index("example/stubs", [*releases, other], tmp_path / "site", data.__getitem__)


def test_drafts_and_unmanifested_releases_are_not_indexed(tmp_path):
    releases, data = release_assets([wheel()])
    releases[0]["draft"] = True
    output = tmp_path / "site"
    assert write_index("example/stubs", releases, output, data.__getitem__) == []
    assert "No recommended wheels published yet" in (output / "index.html").read_text()


def test_install_command_uses_latest_recommended_revision(tmp_path):
    releases, data = release_assets([wheel("3.58.1"), wheel("3.58.1.post2"), wheel()])
    output = tmp_path / "site"
    write_index("example/stubs", releases, output, data.__getitem__)
    command = (output / "index.html").read_text().split("<pre><code>")[1].split("</code></pre>")[0]
    assert "gi_base_stubs-3.58.1.post2-py3-none-any.whl#sha256=" in command
    assert "gi_base_stubs-3.58.1-py3-none-any.whl" not in command
    assert "+glib" not in command


def test_rejects_mislabeled_native_environment(tmp_path):
    releases, data = release_assets([wheel("3.58.1+glib2.80")])
    with pytest.raises(ValueError, match="Native environment mismatch"):
        write_index("example/stubs", releases, tmp_path / "site", data.__getitem__)


def test_mixed_generator_and_stub_index(tmp_path):
    releases, data = release_assets([wheel()])
    entry, blob = wheel("0.1.0", "gi-stub-gen")
    prefix = "https://github.com/example/stubs/releases/download/v0.1.0/"
    manifest = dict(format_version=1, source_commit="a" * 40, wheels=[entry])
    extra = {prefix + "generator-build.json": json.dumps(manifest).encode(), prefix + entry["filename"]: blob}
    data.update(extra)
    releases.append(dict(tag_name="v0.1.0", assets=[dict(name=url.rsplit("/", 1)[-1], browser_download_url=url) for url in extra]))
    output = tmp_path / "site"
    assert len(write_index("example/stubs", releases, output, data.__getitem__)) == 2
    assert entry["filename"] in (output / "simple/gi-stub-gen/index.html").read_text()
    assert "gstreamer-oci binding indexes" in (output / "index.html").read_text()


@pytest.mark.parametrize("requirement", ["Requires-Dist: gst-python-binding\n", "Requires-Dist: GST.Python.Binding\n", "Requires-Dist: thing @ file:///opt/wheel/a.whl\n", "Provides-Extra: gst\n"])
def test_generator_has_no_private_binding_dependency(requirement):
    entry, blob = wheel("0.1.0", "gi-stub-gen", requirement)
    with pytest.raises(ValueError):
        validate_wheel(entry, blob)
