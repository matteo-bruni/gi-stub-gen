"""Release preparation and GitHub mutations are tested with isolated files and fake APIs."""

import hashlib
import json
from pathlib import Path
import platform
import subprocess
import zipfile

import pytest
import tomlkit

from gi_stub_gen import publish
from tests.test_wheel_index import wheel


@pytest.mark.parametrize("value", ["1.0rc1", "1.0.dev1", "1.0+local", "v1.0", "1!1.0", "1.0;echo bad"])
def test_rejects_nonstable_or_noncanonical_versions(value):
    with pytest.raises(ValueError):
        publish.stable_version(value)


def test_update_only_versions(tmp_path):
    project = '[project]\nname="gi-stub-gen"\nversion="0.0.1"\ndependencies=["pygobject>=3.56.1"]\n'
    lock = '[[package]]\nname="gi-stub-gen"\nversion="0.0.1"\n[[package]]\nname="pygobject"\nversion="3.58.1"\n'
    (tmp_path / "pyproject.toml").write_text(project)
    (tmp_path / "uv.lock").write_text(lock)
    publish.update_version(tmp_path, "0.1.0")
    assert (tmp_path / "pyproject.toml").read_text() == project.replace('"0.0.1"', '"0.1.0"')
    assert (tmp_path / "uv.lock").read_text() == lock.replace('"0.0.1"', '"0.1.0"')
    with pytest.raises(ValueError, match="backwards"):
        publish.update_version(tmp_path, "0.0.1")


def image_api():
    releases, blobs = {}, {}
    for ubuntu in ("24.04", "26.04"):
        tag = f"gst-python-binding-1.28.8-ubuntu-{ubuntu}-base-non-free-r2"
        release: dict = dict(draft=False, prerelease=False, assets=[])
        for python in ("3.12", "3.14"):
            name = f"py{python}-build-metadata.json"
            url = f"https://github.com/matteo-bruni/gstreamer-oci/releases/download/{tag}/{name}"
            release["assets"].append(dict(name=name, browser_download_url=url))
            blobs[url] = json.dumps(dict(python_version=python, base_image="ubuntu", base_tag=ubuntu,
                build_profile="base", variant="non-free", image_target="runtime", build_type="release",
                release_revision=2, release_tag=tag, image_ref="ghcr.io/matteo-bruni/gstreamer@sha256:" + "a" * 64,
                image_digest="sha256:" + "a" * 64, build=dict(gstreamer_version="1.28.8"))).encode()
        releases[f"repos/matteo-bruni/gstreamer-oci/releases/tags/{tag}"] = release
    return releases, blobs


def test_selects_exact_four_images_and_fails_without_metadata():
    releases, blobs = image_api()
    images = publish.resolve_images("1.28.8", 2, releases.get, blobs.__getitem__)
    assert {(i["ubuntu"], i["python"]) for i in images} == {(u, p) for u in ("24.04", "26.04") for p in ("3.12", "3.14")}
    assert all("@sha256:" in i["image"] for i in images)
    with pytest.raises(ValueError, match="Missing image release"):
        publish.resolve_images("1.28.8", 1, releases.get, blobs.__getitem__)
    key = next(iter(blobs))
    value = json.loads(blobs[key])
    value["base_tag"] = "wrong"
    blobs[key] = json.dumps(value).encode()
    with pytest.raises(ValueError, match="metadata mismatch"):
        publish.resolve_images("1.28.8", 2, releases.get, blobs.__getitem__)


def generator_api():
    entry, blob = wheel("0.1.0", "gi-stub-gen")
    prefix = "https://github.com/example/stubs/releases/download/v0.1.0/"
    manifest = dict(format_version=1, source_commit="a" * 40, wheels=[entry])
    data = {prefix + "generator-build.json": json.dumps(manifest).encode(), prefix + entry["filename"]: blob}
    release = dict(draft=False, prerelease=False, assets=[dict(name=url.rsplit("/", 1)[-1], browser_download_url=url) for url in data])
    responses = {"repos/example/stubs/releases/tags/v0.1.0": release, "repos/example/stubs/commits/v0.1.0": dict(sha="a" * 40)}
    return responses, data


def test_generator_download_and_tag_identity():
    responses, data = generator_api()
    manifest, blob = publish.generator_release("example/stubs", "0.1.0", responses.get, data.__getitem__)
    assert hashlib.sha256(blob).hexdigest() == manifest["wheels"][0]["sha256"]
    responses["repos/example/stubs/commits/v0.1.0"]["sha"] = "b" * 40
    with pytest.raises(ValueError, match="tag moved"):
        publish.generator_release("example/stubs", "0.1.0", responses.get, data.__getitem__)


def test_complete_generator_release_only_verifies(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(publish, "api", lambda endpoint: dict(existing=True))
    monkeypatch.setattr(publish, "generator_release", lambda *args: calls.append(args))
    monkeypatch.setattr(publish, "run", lambda *args, **kwargs: pytest.fail("Must not build or write"))
    publish.generator(tmp_path, tmp_path, "example/stubs", "0.1.0")
    assert calls == [("example/stubs", "0.1.0")]


def test_container_uses_public_author_metadata_without_copying_credentials(monkeypatch, tmp_path):
    root, work = tmp_path / "source", tmp_path / "work"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nauthors=[{name="Author Name",email="author@example.com"}]\n')
    (root / ".env").write_text("PRIVATE=not-for-the-container\n")
    (root / ".git").mkdir()
    wheel = tmp_path / "generator.whl"
    wheel.write_bytes(b"wheel")
    calls = []
    monkeypatch.setattr(publish, "run", lambda *args, **kwargs: "")
    monkeypatch.setattr(publish.subprocess, "run", lambda args, **kwargs: calls.append(args))
    image = dict(ubuntu="26.04", python="3.14", image="immutable-image")
    target = publish.container(root, work, image, wheel, "generator")
    assert not (target / ".env").exists() and not (target / ".git").exists()
    assert "STUB_AUTHOR_NAME=Author Name" in calls[0] and "STUB_AUTHOR_EMAIL=author@example.com" in calls[0]
    assert not any("TOKEN" in arg for arg in calls[0])


def test_reuses_published_bytes_and_rejects_changed_payload(tmp_path):
    entry, blob = wheel()
    path = tmp_path / entry["filename"]
    path.write_bytes(blob + b"new ZIP timestamp representation")
    manifest = tmp_path / "stub-build-glib2.88.json"
    manifest.write_text(json.dumps(dict(wheels=[entry])))
    publish.reuse_wheels(tmp_path, [dict(entry, url="original")], lambda url: blob)
    assert path.read_bytes() == blob
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("gi-stubs/new.pyi", "changed: int\n")
    with pytest.raises(ValueError, match="new revision"):
        publish.reuse_wheels(tmp_path, [dict(entry, url="original")], lambda url: blob)


def test_publish_uploads_all_assets_before_publishing(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(publish, "run", lambda *args, **kwargs: calls.append(args))
    (tmp_path / "test.whl").write_bytes(b"wheel")
    (tmp_path / "generator-build.json").write_text("{}")
    publish.publish("example/stubs", "v0.1.0", "a" * 40, tmp_path)
    assert "--draft" in calls[0] and str(tmp_path / "test.whl") in calls[0]
    assert str(tmp_path / "generator-build.json") in calls[0]
    assert calls[1] == ("gh", "release", "edit", "v0.1.0", "--repo", "example/stubs", "--draft=false")


def test_existing_stub_release_requires_all_wheels_and_same_inputs(monkeypatch):
    generator = dict(source_commit="a" * 40, wheels=[dict(version="0.1.0")])
    images = [dict(image="digest")]
    release = dict(draft=False, prerelease=False, assets=[dict(name=f"stub-build-{n}.json", browser_download_url=str(n)) for n in (1, 2)])
    entries = [dict(name=name, version="1.0.post1") for name in publish.PACKAGES for _ in range(3)]
    monkeypatch.setattr(publish, "write_index", lambda *args: entries)
    manifest = dict(source_commit="a" * 40, generator=generator["wheels"][0], images=images)
    publish.verify_stub_release("example/stubs", release, images, generator, 1, lambda url: json.dumps(manifest).encode())
    with pytest.raises(ValueError, match="different generator or images"):
        publish.verify_stub_release("example/stubs", release, [], generator, 1, lambda url: json.dumps(manifest).encode())
    entries.pop()
    with pytest.raises(ValueError, match="twelve wheels"):
        publish.verify_stub_release("example/stubs", release, images, generator, 1, lambda url: json.dumps(manifest).encode())


@pytest.mark.parametrize("failure", [None, "branch", "push"])
def test_generator_orchestration_pushes_only_after_checks(monkeypatch, tmp_path, failure):
    root, work = tmp_path / "source", tmp_path / "work"
    root.mkdir()
    work.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname="gi-stub-gen"\nversion="0.0.1"\n')
    (root / "uv.lock").write_text('[[package]]\nname="gi-stub-gen"\nversion="0.0.1"\n')
    calls = []
    monkeypatch.setattr(publish, "api", lambda endpoint: None)
    branch_checks = 0

    def repository_state(endpoint):
        nonlocal branch_checks
        if "/commits/" in endpoint:
            branch_checks += 1
        sha = "b" * 40 if failure == "branch" and branch_checks == 2 else "a" * 40
        return dict(default_branch="main", sha=sha)

    monkeypatch.setattr(publish, "required_api", repository_state)
    monkeypatch.setattr(publish, "resolve_images", lambda *args: [dict(ubuntu="26.04", python="3.14")])
    monkeypatch.setattr(publish, "container", lambda *args: calls.append(("checked",)))
    monkeypatch.setattr(publish, "publish", lambda *args: calls.append(("published",)))

    def fake_run(*args, **kwargs):
        calls.append(args)
        if args[:2] == ("git", "push") and failure == "push":
            raise publish.subprocess.CalledProcessError(1, args)
        if args[:2] == ("uv", "build"):
            output = work / "assets"
            output.mkdir()
            entry, blob = wheel("0.1.0", "gi-stub-gen")
            (output / entry["filename"]).write_bytes(blob)
        if args[:3] == ("git", "rev-parse", "HEAD"):
            return "a" * 40
        if args[:2] == ("git", "diff"):
            return "version changed"
        return ""

    monkeypatch.setattr(publish, "run", fake_run)
    if failure:
        with pytest.raises((ValueError, publish.subprocess.CalledProcessError)):
            publish.generator(root, work, "example/stubs", "0.1.0")
        assert ("published",) not in calls
        return
    publish.generator(root, work, "example/stubs", "0.1.0")
    push = next(c for c in calls if c[:2] == ("git", "push"))
    assert "--atomic" in push and "HEAD:refs/heads/main" in push and "refs/tags/v0.1.0" in push
    assert calls.index(("checked",)) < calls.index(push) < calls.index(("published",))


def test_stub_orchestration_uses_released_commit_and_checks_eight_consumers(monkeypatch, tmp_path):
    entry, blob = wheel("0.1.0", "gi-stub-gen")
    manifest = dict(source_commit="a" * 40, wheels=[entry])
    images = [dict(ubuntu=u, python=p, image=f"image-{u}-{p}") for u in ("24.04", "26.04") for p in ("3.12", "3.14")]
    calls = []
    monkeypatch.setattr(publish, "resolve_images", lambda *args: images)
    monkeypatch.setattr(publish, "generator_release", lambda *args: (manifest, blob))
    monkeypatch.setattr(publish, "api", lambda *args: None)
    monkeypatch.setattr(publish, "release_catalog", lambda *args: [])
    monkeypatch.setattr(publish, "run", lambda *args, **kwargs: calls.append(args))
    monkeypatch.setattr(publish, "publish", lambda *args: calls.append(("published",)))

    def fake_container(root, work, image, generator_wheel, stage, revision):
        assert generator_wheel.read_bytes() == blob
        cell = work / (image["ubuntu"] + image["python"])
        package = cell / "stubs/base/src/gi-stubs"
        package.mkdir(parents=True)
        (package / "__init__.pyi").write_text("value: int\n")
        output = cell / ".release-output"
        output.mkdir()
        logs = cell / ".release-logs"
        logs.mkdir()
        (logs / "environment.json").write_text(json.dumps(dict(glib_runtime="2.80.5", gstreamer="1.28.8")))
        glib = "2.80" if image["ubuntu"] == "24.04" else "2.88"
        entries = []
        for name in publish.PACKAGES:
            public = "1.28.8" if name == "gi-gst-stubs" else "3.58.1"
            versions = [public + "+glib" + glib]
            if image["ubuntu"] == "26.04" and image["python"] == "3.14":
                versions.append(public)
            for version in versions:
                info, data = wheel(version, name)
                entries.append(info)
                (output / info["filename"]).write_bytes(data)
        (output / f"stub-build-glib{glib}.json").write_text(json.dumps(dict(wheels=entries)))
        return cell

    def fake_consumer(args, **kwargs):
        selected = Path(args[args.index("-v") + 1].split(":")[0]) / args[-1].removeprefix("/code/")
        assert len(list(selected.glob("*.whl"))) == 4
        calls.append(("consumer",))

    monkeypatch.setattr(publish, "container", fake_container)
    monkeypatch.setattr(publish.subprocess, "run", fake_consumer)
    publish.stubs(tmp_path, tmp_path, "example/stubs", "0.1.0", "1.28.8", 1, 0)
    assert ("git", "checkout", "--detach", "a" * 40) in calls
    assert calls.count(("consumer",)) == 8
    assert calls[-1] == ("published",)
    assert len(list((tmp_path / "assets").glob("*.whl"))) == 12
    verification = json.loads((tmp_path / "assets/verification.json").read_text())
    assert len(verification["environments"]) == 4
    assert all(value["glib_runtime"] == "2.80.5" for value in verification["environments"].values())


def test_python_parity_rejects_missing_files_and_changed_signatures(tmp_path):
    roots = [tmp_path / "312", tmp_path / "314"]
    for root in roots:
        target = root / "stubs/base/src/gi-stubs/repository/Gst.pyi"
        target.parent.mkdir(parents=True)
        target.write_text('"""Python-dependent documentation."""\ndef func() -> int: ...\n')
    publish.compare_python(*roots)
    target = roots[1] / "stubs/base/src/gi-stubs/repository/Gst.pyi"
    target.write_text('def func() -> int:\n    """Documentation is a valid stub body."""\n')
    assert publish.compare_python(*roots) == ["stubs/base/src/gi-stubs/repository/Gst.pyi"]
    target.write_text("def func() -> str: ...\n")
    with pytest.raises(ValueError, match="declarations differ"):
        publish.compare_python(*roots)


def test_workflows_keep_native_bindings_optional():
    root = Path(__file__).resolve().parents[1]
    project = tomlkit.parse((root / "pyproject.toml").read_text())
    assert "gst-python-binding" not in str(project["project"]["dependencies"])
    assert "gst" not in project["project"].get("optional-dependencies", {})
    assert project["dependency-groups"]["gst"] == ["gst-python-binding"]
    assert len(list((root / ".github/workflows").glob("*.yml"))) == 2


def test_dependency_script_rejects_wrong_ubuntu_without_installing():
    root = Path(__file__).resolve().parents[1]
    current = platform.freedesktop_os_release()["VERSION_ID"]
    wrong = "26.04" if current == "24.04" else "24.04"
    result = subprocess.run(["bash", str(root / f"scripts/ubuntu-{wrong}/install_deps.sh")], capture_output=True, text=True)
    assert result.returncode == 1
    assert f"Expected Ubuntu {wrong}, found {current}" in result.stderr
