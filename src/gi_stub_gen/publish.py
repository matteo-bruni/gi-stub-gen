"""Release orchestration for GitHub Actions; unit tests replace GitHub and Git writes."""

import argparse
import ast
from email.parser import BytesParser
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import quote
import zipfile

from packaging.version import Version
import tomlkit

from gi_stub_gen.wheel_index import fetch, require, validate_wheel, write_index
from gi_stub_gen.release import PACKAGES

OCI_REPOSITORY = "matteo-bruni/gstreamer-oci"
CURRENT_GSTREAMER = "1.28.8"
PACKAGE_GROUPS = {
    "all": PACKAGES,
    "gst": ("gi-gst-stubs",),
    "base": ("gi-base-stubs",),
    "graphics": ("gi-graphics-core-stubs",),
    "gtk": ("gi-gtk-stubs",),
}


def run(*args: str, cwd: Path | None = None) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def api(endpoint: str):
    result = subprocess.run(["gh", "api", endpoint], capture_output=True, text=True)
    if result.returncode and "(HTTP 404)" in result.stderr:
        return None
    require(result.returncode == 0, result.stderr)
    return json.loads(result.stdout)


def required_api(endpoint: str):
    value = api(endpoint)
    if value is None:
        raise ValueError(f"GitHub resource missing: {endpoint}")
    return value


def stable_version(value: str) -> str:
    parsed = Version(value)
    require(str(parsed) == value and not parsed.is_prerelease and not parsed.is_devrelease
            and parsed.local is None and parsed.epoch == 0, "Use a canonical stable public version")
    return value


def update_version(root: Path, value: str) -> None:
    """Change only project versions; retain the lock's native wheels and all dependencies."""
    stable_version(value)
    project = tomlkit.parse((root / "pyproject.toml").read_text())
    lock = tomlkit.parse((root / "uv.lock").read_text())
    current = project["project"]["version"]
    require(Version(value) >= Version(str(current)), "Version must not go backwards")
    package = next(p for p in lock["package"] if p["name"] == "gi-stub-gen")
    require(package["version"] == current, "Project and lock versions disagree")
    project["project"]["version"] = value
    package["version"] = value
    (root / "pyproject.toml").write_text(tomlkit.dumps(project))
    (root / "uv.lock").write_text(tomlkit.dumps(lock))


def resolve_images(gst: str, revision: int, get=api, download=fetch) -> list[dict]:
    """Resolve the fixed Ubuntu/Python matrix from OCI release metadata, never moving tags."""
    require(re.fullmatch(r"\d+\.\d+\.\d+", gst) is not None, "Expected numeric GStreamer X.Y.Z")
    require(revision >= 1, "Image revisions start at 1")
    images = []
    for ubuntu in ("24.04", "26.04"):
        tag = f"gst-python-binding-{gst}-ubuntu-{ubuntu}-base-non-free"
        if revision > 1:
            tag += f"-r{revision}"
        release = get(f"repos/{OCI_REPOSITORY}/releases/tags/{tag}")
        if release is None:
            raise ValueError(f"Missing image release: {tag}")
        require(not release["draft"] and not release["prerelease"], f"Missing stable image release: {tag}")
        for python in ("3.12", "3.14"):
            name = f"py{python}-build-metadata.json"
            asset = next((a for a in release["assets"] if a["name"] == name), None)
            if asset is None:
                raise ValueError(f"Missing {name} in {tag}")
            prefix = f"https://github.com/{OCI_REPOSITORY}/releases/download/{quote(tag, safe='')}/"
            require(asset["browser_download_url"] == prefix + name, "Unexpected image metadata URL")
            metadata = json.loads(download(asset["browser_download_url"]))
            expected = dict(python_version=python, base_image="ubuntu", base_tag=ubuntu,
                            build_profile="base", variant="non-free", image_target="runtime",
                            build_type="release", release_revision=revision, release_tag=tag)
            require(all(metadata.get(k) == v for k, v in expected.items()), f"Image metadata mismatch: {tag}/{python}")
            image = metadata["image_ref"]
            require(re.fullmatch(r"ghcr\.io/matteo-bruni/gstreamer@sha256:[0-9a-f]{64}", image) is not None,
                    "Expected immutable GStreamer image reference")
            require(image.endswith("@" + metadata["image_digest"]), "Image digest mismatch")
            require(metadata["build"]["gstreamer_version"] == gst, "Wrong native GStreamer version")
            images.append(dict(ubuntu=ubuntu, python=python, image=image, metadata=metadata))
    return images


def release_catalog(repository: str) -> list[dict]:
    batches = json.loads(run("gh", "api", "--paginate", "--slurp", f"repos/{repository}/releases?per_page=100"))
    with tempfile.TemporaryDirectory() as directory:
        return write_index(repository, [r for batch in batches for r in batch], Path(directory) / "index")


def generator_release(repository: str, value: str, get=api, download=fetch) -> tuple[dict, bytes]:
    """Download a published wheel only after checking its manifest, source tag and checksum."""
    stable_version(value)
    tag = "v" + value
    release = get(f"repos/{repository}/releases/tags/{tag}")
    if release is None:
        raise ValueError(f"Missing generator release: {tag}")
    require(not release["draft"] and not release["prerelease"], f"Missing stable generator release: {tag}")
    prefix = f"https://github.com/{repository}/releases/download/{tag}/"
    assets = {a["name"]: a["browser_download_url"] for a in release["assets"]}
    require(assets.get("generator-build.json") == prefix + "generator-build.json", "Missing generator manifest")
    manifest = json.loads(download(assets["generator-build.json"]))
    require(manifest["format_version"] == 1 and len(manifest["wheels"]) == 1, "Invalid generator manifest")
    commit = manifest["source_commit"]
    require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "Invalid generator commit")
    actual = get(f"repos/{repository}/commits/{tag}")
    require(actual is not None and actual["sha"] == commit, "Generator tag moved")
    entry = manifest["wheels"][0]
    require(entry["name"] == "gi-stub-gen" and entry["version"] == value, "Wrong generator version")
    require(assets.get(entry["filename"]) == prefix + entry["filename"], "Missing generator wheel")
    data = download(assets[entry["filename"]])
    validate_wheel(entry, data)
    return manifest, data


def wheel_entry(path: Path) -> dict:
    data = path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(data)) as wheel:
        metadata = BytesParser().parsebytes(wheel.read(next(n for n in wheel.namelist() if n.endswith(".dist-info/METADATA"))))
    entry = dict(filename=path.name, name=str(metadata["Name"]), version=str(metadata["Version"]),
                 requires_python=str(metadata["Requires-Python"]), canonical=Version(str(metadata["Version"])).local is None,
                 sha256=hashlib.sha256(data).hexdigest())
    validate_wheel(entry, data)
    return entry


def wheel_contents(data: bytes) -> dict[str, tuple[int, bytes]]:
    """Ignore ZIP timestamps, regenerated RECORD hashes and only the packaging Date header."""
    with zipfile.ZipFile(io.BytesIO(data)) as wheel:
        return {name: (wheel.getinfo(name).external_attr,
                       re.sub(rb"(?m)^Date:\s*\d{4}-\d{2}-\d{2}\s*$", b"Date: <NORMALIZED>", wheel.read(name))
                       if name.endswith(".pyi") else wheel.read(name))
                for name in wheel.namelist() if not name.endswith(".dist-info/RECORD")}


def reuse_wheels(output: Path, catalog: list[dict], download=fetch) -> None:
    """Keep published bytes for equivalent rebuilds; never publish discordant filenames."""
    existing = {entry["filename"]: entry for entry in catalog}
    for manifest_path in output.glob("stub-build-*.json"):
        manifest = json.loads(manifest_path.read_text())
        for entry in manifest["wheels"]:
            previous = existing.get(entry["filename"])
            if previous is None:
                continue
            data = download(previous["url"])
            validate_wheel(previous, data)
            path = output / entry["filename"]
            require(wheel_contents(data) == wheel_contents(path.read_bytes()),
                    f"Changed published wheel {path.name}; choose a new revision (.postN)")
            path.write_bytes(data)
            entry["sha256"] = previous["sha256"]
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


def _stub_payload(data: bytes) -> tuple[dict[str, tuple[int, bytes]], str, list[str]]:
    """Compare exported stubs and installation requirements, independently of the build backend."""
    contents = wheel_contents(data)
    metadata = BytesParser().parsebytes(next(value[1] for name, value in contents.items()
                                           if name.endswith(".dist-info/METADATA")))
    return ({name: value for name, value in contents.items() if name.startswith("gi-stubs/")},
            str(metadata["Requires-Python"]), sorted(metadata.get_all("Requires-Dist", [])))


def published_dependency(candidate: dict, data: bytes, ubuntu: str, catalog: list[dict], download=fetch) -> tuple[dict, bytes]:
    """Reuse an unchanged, matching published package without rebuilding or republishing it."""
    expected = Version(candidate["version"])
    matches = [entry for entry in catalog if entry["name"] == candidate["name"]
               and Version(entry["version"]).base_version == expected.base_version
               and Version(entry["version"]).local == expected.local
               and ubuntu in entry.get("ubuntu_versions", [])]
    require(bool(matches), f"No published {candidate['name']} matching {expected} on Ubuntu {ubuntu}; select all packages")
    payload = _stub_payload(data)
    for entry in sorted(matches, key=lambda entry: Version(entry["version"]), reverse=True):
        previous = download(entry["url"])
        validate_wheel(entry, previous)
        if _stub_payload(previous) == payload:
            return entry, previous
    raise ValueError(f"Unselected package {candidate['name']} has changed; select all packages to publish it")


def verify_stub_release(repository: str, release: dict, images: list[dict], generator: dict,
                        revision: int, download=fetch, *, packages: tuple[str, ...] = PACKAGES) -> None:
    """Allow an index-only retry only for a complete release made with the same inputs."""
    require(not release["draft"] and not release["prerelease"], "Existing release is incomplete")
    with tempfile.TemporaryDirectory() as directory:
        entries = write_index(repository, [release], Path(directory) / "index", download)
    require(len(entries) == 3 * len(packages) and all(sum(e["name"] == name for e in entries) == 3 for name in packages),
            "Existing stub release must contain exactly three wheels per selected package")
    require(all(Version(e["version"]).post == (revision or None) for e in entries), "Wrong stub revision")
    assets = [a for a in release["assets"] if a["name"].startswith("stub-build-") and a["name"].endswith(".json")]
    require(len(assets) == 2, "Expected two native build manifests")
    for asset in assets:
        manifest = json.loads(download(asset["browser_download_url"]))
        require(tuple(manifest.get("packages", PACKAGES)) == packages, "Existing release uses different packages")
        require(manifest.get("source_commit") == generator["source_commit"] and manifest.get("generator") == generator["wheels"][0]
                and manifest.get("images") == images, "Existing release uses different generator or images; use a new revision")


def container(root: Path, work: Path, image: dict, wheel: Path, stage: str, revision: int = 0) -> Path:
    """Run a released wheel in an isolated source copy, without passing GitHub credentials."""
    target = work / f"{stage}-{image['ubuntu']}-{image['python']}"
    shutil.copytree(root, target, ignore=shutil.ignore_patterns(".git", ".env", ".venv", "__pycache__", "internal", ".release-work"))
    author = tomlkit.parse((root / "pyproject.toml").read_text())["project"]["authors"][0]
    inputs = target / ".release-input"
    inputs.mkdir()
    shutil.copy2(wheel, inputs / wheel.name)
    (inputs / "image.json").write_text(json.dumps(image))
    run("docker", "pull", image["image"])
    subprocess.run(["docker", "run", "--rm", "--platform", "linux/amd64", "-v", f"{target}:/code", "-w", "/code",
                    "-e", "UV_NO_SYNC=1", "-e", "UV_PYTHON=/opt/uv/venv/bin/python", "-e", "UV_PYTHON_DOWNLOADS=never",
                    "-e", f"STUB_AUTHOR_NAME={author['name']}", "-e", f"STUB_AUTHOR_EMAIL={author['email']}",
                    image["image"], "bash", "scripts/check-release.sh", stage, image["image"], str(revision), image["ubuntu"]], check=True)
    return target


def compare_python(left: Path, right: Path) -> list[str]:
    """Compare API structure; runtime docstrings are reported separately from Python syntax."""
    def signatures(root: Path) -> dict[str, str]:
        result = {}
        for path in root.glob("stubs/*/src/**/*.pyi"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                        node.body.pop(0)
                        if not node.body and not isinstance(node, ast.Module):
                            node.body = [ast.Expr(value=ast.Constant(value=Ellipsis))]
            result[str(path.relative_to(root))] = ast.dump(tree)
        return result
    require(signatures(left) == signatures(right), "Python 3.12/3.14 stub inventories or API declarations differ")
    return [str(path.relative_to(left)) for path in left.glob("stubs/*/src/**/*.pyi")
            if re.sub(r"(?m)^Date:\s*\d{4}-\d{2}-\d{2}\s*$", "Date: <NORMALIZED>", path.read_text())
            != re.sub(r"(?m)^Date:\s*\d{4}-\d{2}-\d{2}\s*$", "Date: <NORMALIZED>", (right / path.relative_to(left)).read_text())]


def publish(repository: str, tag: str, commit: str, output: Path) -> None:
    """Create a draft with all assets first, then publish it without replacing files."""
    notes = output / "release-notes.md"
    notes.write_text(f"Source: {commit}\n\nUniversal Python 3.12+ wheels. See the JSON manifests for checksums and build provenance.\n")
    run("gh", "release", "create", tag, "--repo", repository, "--verify-tag", "--draft", "--title", tag,
        "--notes-file", str(notes), *map(str, sorted(output.glob("*.whl"))), *map(str, sorted(output.glob("*.json"))))
    run("gh", "release", "edit", tag, "--repo", repository, "--draft=false")


def generator(root: Path, work: Path, repository: str, value: str) -> None:
    """Verify the new generator before atomically pushing its version commit and release tag."""
    stable_version(value)
    tag = "v" + value
    if api(f"repos/{repository}/releases/tags/{tag}") is not None:
        generator_release(repository, value)
        return
    start = run("git", "rev-parse", "HEAD", cwd=root)
    branch = required_api(f"repos/{repository}")["default_branch"]
    require(required_api(f"repos/{repository}/commits/{quote(branch, safe='')}")["sha"] == start, "Run from the current default branch")
    update_version(root, value)
    output = work / "assets"
    run("uv", "build", "--wheel", str(root), "--out-dir", str(output))
    wheel = next(output.glob("*.whl"))
    entry = wheel_entry(wheel)
    require(entry["version"] == value, "Generator build version mismatch")
    image = next(i for i in resolve_images(CURRENT_GSTREAMER, 1) if i["ubuntu"] == "26.04" and i["python"] == "3.14")
    container(root, work, image, wheel, "generator")
    require(required_api(f"repos/{repository}/commits/{quote(branch, safe='')}")["sha"] == start, "Default branch advanced; rerun")
    if run("git", "diff", "--", "pyproject.toml", "uv.lock", cwd=root):
        run("git", "add", "pyproject.toml", "uv.lock", cwd=root)
        run("git", "-c", "user.name=github-actions[bot]", "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
            "commit", "-m", f"Release gi-stub-gen {value}", cwd=root)
    commit = run("git", "rev-parse", "HEAD", cwd=root)
    (output / "generator-build.json").write_text(json.dumps(dict(format_version=1, source_commit=commit, wheels=[entry]), indent=2) + "\n")
    # Atomic, non-forced push: a racing branch update must not leave a release tag behind.
    run("git", "tag", tag, cwd=root)
    run("git", "push", "--atomic", "origin", f"HEAD:refs/heads/{branch}", f"refs/tags/{tag}", cwd=root)
    publish(repository, tag, commit, output)


def stubs(root: Path, work: Path, repository: str, gen: str, gst: str, image_revision: int, revision: int,
          packages: str = "all") -> None:
    """Build native variants, test recommended wheels across the matrix, then publish once."""
    require(revision >= 0, "Stub revision must be non-negative")
    require(packages in PACKAGE_GROUPS, "Unknown package group")
    selected_packages = PACKAGE_GROUPS[packages]
    stable_version(gen)
    images = resolve_images(gst, image_revision)
    manifest, data = generator_release(repository, gen)
    scope = "" if packages == "all" else f"-{packages}"
    tag = f"stubs-gst{gst}-gen{gen}{scope}-r{revision}"
    existing = api(f"repos/{repository}/releases/tags/{tag}")
    if existing is not None:
        verify_stub_release(repository, existing, images, manifest, revision, packages=selected_packages)
        return
    catalog = release_catalog(repository)
    source = work / "source"
    run("git", "clone", "--no-checkout", "--", f"https://github.com/{repository}.git", str(source))
    run("git", "checkout", "--detach", manifest["source_commit"], cwd=source)
    wheel = work / manifest["wheels"][0]["filename"]
    wheel.write_bytes(data)
    cells = {}
    output = work / "assets"
    output.mkdir()
    for image in images:
        cell = container(source, work, image, wheel, "stubs", revision)
        cells[image["ubuntu"], image["python"]] = cell
        if image["python"] == "3.14":
            release_output = cell / ".release-output"
            for path in release_output.glob("stub-build-*.json"):
                info = json.loads(path.read_text())
                info["wheels"] = [entry for entry in info["wheels"] if entry["name"] in selected_packages]
                require({entry["name"] for entry in info["wheels"]} == set(selected_packages), "Missing selected packages")
                info["packages"] = list(selected_packages)
                # uv also writes .gitignore here; publish only selected wheels and their manifest.
                for entry in info["wheels"]:
                    target = output / entry["filename"]
                    require(not target.exists(), f"Duplicate artifact: {target.name}")
                    shutil.copy2(release_output / target.name, target)
                require(not (output / path.name).exists(), f"Duplicate artifact: {path.name}")
                (output / path.name).write_text(json.dumps(info, indent=2) + "\n")
    documentation_differences = {ubuntu: compare_python(cells[ubuntu, "3.12"], cells[ubuntu, "3.14"])
                                 for ubuntu in ("24.04", "26.04")}
    reuse_wheels(output, catalog)
    for path in output.glob("stub-build-*.json"):
        info = json.loads(path.read_text())
        info.update(source_commit=manifest["source_commit"], generator=manifest["wheels"][0], images=images)
        path.write_text(json.dumps(info, indent=2) + "\n")
    # Both native and recommended wheels must work in every corresponding runtime.
    dependencies: dict[tuple[str, str], tuple[dict, bytes]] = {}
    for image in images:
        cell = cells[image["ubuntu"], image["python"]]
        sets = [cells[image["ubuntu"], "3.14"] / ".release-output", cells["26.04", "3.14"] / ".release-output"]
        for number, wheels in enumerate(sets):
            selected = cell / f".consumer-{number}"
            selected.mkdir()
            for path in wheels.glob("stub-build-*.json"):
                for entry in json.loads(path.read_text())["wheels"]:
                    if entry["canonical"] != (number == 1):
                        continue
                    if entry["name"] in selected_packages:
                        shutil.copy2(output / entry["filename"], selected / entry["filename"])
                    else:
                        ubuntu = image["ubuntu"] if number == 0 else "26.04"
                        key = (ubuntu, entry["filename"])
                        if key not in dependencies:
                            dependencies[key] = published_dependency(entry, (wheels / entry["filename"]).read_bytes(), ubuntu, catalog)
                        previous, dependency_data = dependencies[key]
                        (selected / previous["filename"]).write_bytes(dependency_data)
            subprocess.run(["docker", "run", "--rm", "-v", f"{cell}:/code", "-w", "/code", image["image"],
                            "bash", "scripts/check-release.sh", "consumers", f"/code/.consumer-{number}"], check=True)
    environments = {f"{u}-{p}": json.loads((cell / ".release-logs/environment.json").read_text())
                    for (u, p), cell in cells.items()}
    reused = {entry["filename"]: entry for entry, _ in dependencies.values()}
    (output / "verification.json").write_text(json.dumps(dict(source_commit=manifest["source_commit"], packages=list(selected_packages),
        reused_wheels=list(reused.values()),
        images=images, environments=environments, python_api_parity=True, documentation_differences=documentation_differences,
        consumer_combinations=8), indent=2) + "\n")
    run("git", "tag", tag, manifest["source_commit"], cwd=source)
    run("git", "push", "origin", f"refs/tags/{tag}", cwd=source)
    publish(repository, tag, manifest["source_commit"], output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("generator").add_argument("--version", required=True)
    stub = commands.add_parser("stubs")
    stub.add_argument("--generator-version", required=True)
    stub.add_argument("--gstreamer-version", required=True)
    stub.add_argument("--image-revision", type=int, default=1)
    stub.add_argument("--revision", type=int, default=0)
    stub.add_argument("--packages", choices=PACKAGE_GROUPS, default="all", help="Publish all packages or one package group")
    args = parser.parse_args()
    repository = os.environ["GITHUB_REPOSITORY"]
    require(re.fullmatch(r"[\w.-]+/[\w.-]+", repository) is not None, "Invalid repository")
    root = Path.cwd()
    work = Path(os.environ["RUNNER_TEMP"]) / "gi-release"
    work.mkdir(exist_ok=False)
    if args.command == "generator":
        generator(root, work, repository, args.version)
    else:
        stubs(root, work, repository, args.generator_version, args.gstreamer_version, args.image_revision, args.revision, args.packages)


if __name__ == "__main__":
    main()
