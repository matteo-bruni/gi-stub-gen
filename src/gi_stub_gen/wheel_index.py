"""Create a static Simple index from validated GitHub release wheels and manifests."""

import argparse
from email.parser import BytesParser
import hashlib
import html
import io
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import quote, unquote
from urllib.request import Request, urlopen
import zipfile

from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.requirements import Requirement
from packaging.version import Version

from gi_stub_gen.release import PACKAGES, validate_native_labels

INDEX_PACKAGES = (*PACKAGES, "gi-stub-gen")
UBUNTU_VERSIONS = ("24.04", "26.04")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "gi-stub-gen-wheel-index"})
    with urlopen(request, timeout=60) as response:
        data = response.read(32 * 1024 * 1024 + 1)
    require(len(data) <= 32 * 1024 * 1024, f"Asset exceeds 32 MiB: {url}")
    return data


def validate_wheel(entry: dict, data: bytes) -> None:
    """Compare filename, package metadata and the producer's checksum."""
    filename = entry["filename"]
    require(Path(filename).name == filename, f"Unsafe filename: {filename}")
    name, version, build, tags = parse_wheel_filename(filename)
    require(name in INDEX_PACKAGES, f"Unexpected package: {name}")
    require(not build, f"Use .postN for release revisions: {filename}")
    require({str(tag) for tag in tags} == {"py3-none-any"}, f"Not universal: {filename}")
    require(name == canonicalize_name(entry["name"]) and version == Version(entry["version"]), f"Manifest mismatch: {filename}")
    require(hashlib.sha256(data).hexdigest() == entry["sha256"], f"Checksum mismatch: {filename}")
    require(entry["canonical"] == (version.local is None), f"Incorrect canonical label: {filename}")
    with zipfile.ZipFile(io.BytesIO(data)) as wheel:
        files = [path for path in wheel.namelist() if path.endswith(".dist-info/METADATA")]
        require(len(files) == 1, f"Expected one METADATA: {filename}")
        directory = files[0].removesuffix("METADATA")
        require(directory == f"{name.replace('-', '_')}-{version}.dist-info/", f"Incorrect dist-info directory: {filename}")
        metadata = BytesParser().parsebytes(wheel.read(files[0]))
        require(canonicalize_name(str(metadata["Name"])) == name and metadata["Version"] == str(version), f"METADATA mismatch: {filename}")
        require(metadata["Requires-Python"] == entry["requires_python"], f"Python requirement mismatch: {filename}")
        if name == "gi-stub-gen":
            requirements = [Requirement(value) for value in metadata.get_all("Requires-Dist", [])]
            require(not any(canonicalize_name(value.name) == "gst-python-binding"
                            or value.url is not None and (value.url.startswith("file:") or "/opt/" in value.url)
                            for value in requirements), f"Private dependency in {filename}")
            require("gst" not in metadata.get_all("Provides-Extra", []), f"Unexpected gst extra: {filename}")
            require("gi-stub-gen = gi_stub_gen.cli.gi_stub_gen:app" in wheel.read(directory + "entry_points.txt").decode(),
                    f"Missing generator entry point: {filename}")
            require(any(path.startswith("gi_stub_gen/templates/") for path in wheel.namelist()),
                    f"Missing templates: {filename}")
        info = BytesParser().parsebytes(wheel.read(directory + "WHEEL"))
        require(info["Root-Is-Purelib"] == "true" and info.get_all("Tag") == ["py3-none-any"], f"Invalid wheel tags: {filename}")


def page(title: str, body: str) -> str:
    return ('<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{html.escape(title)}</title>'
            '<style>body{font-family:system-ui,sans-serif;line-height:1.5;max-width:76rem;margin:2rem auto;padding:0 1rem}'
            'table{border-collapse:collapse}th,td{text-align:left;vertical-align:top;padding:.5rem;border-bottom:1px solid #ddd}'
            'a{overflow-wrap:anywhere}pre{overflow-x:auto;padding:1rem;background:#f5f5f5}</style>'
            f'</head><body>\n{body}\n</body></html>\n')


def _write_simple_index(output: Path, catalog: list[dict]) -> None:
    """Write package links for one view of the already validated catalog."""
    links = []
    for name in INDEX_PACKAGES:
        entries = sorted((entry for entry in catalog if entry["name"] == name),
                         key=lambda entry: Version(entry["version"]), reverse=True)
        target = output / "simple" / name
        target.mkdir(parents=True)
        body = "\n".join(
            f'<a href="{html.escape(entry["url"], quote=True)}#sha256={entry["sha256"]}" '
            f'data-requires-python="{html.escape(entry["requires_python"], quote=True)}">'
            f'{html.escape(entry["filename"])}</a><br>' for entry in entries
        )
        (target / "index.html").write_text(page(name, body))
        links.append(f'<a href="{name}/">{name}</a><br>')
    (output / "simple/index.html").write_text(page("GI stub packages", "\n".join(links)))


def write_index(repository: str, releases: list[dict], output: Path, download=fetch) -> list[dict]:
    """Adapt the gstreamer-oci index pattern; wheel assets remain on GitHub Releases."""
    require(re.fullmatch(r"[\w.-]+/[\w.-]+", repository) is not None, "Expected owner/repository")
    require(not output.exists(), f"Output already exists: {output}")
    catalog: list[dict] = []
    seen: dict[str, dict] = {}
    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        tag = release["tag_name"]
        prefix = f"https://github.com/{repository}/releases/download/{quote(tag, safe='')}/"
        assets = {asset["name"]: asset for asset in release["assets"]}

        def asset(name: str) -> tuple[str, bytes]:
            require(name in assets and Path(name).name == name, f"Missing/unsafe asset: {name}")
            url = assets[name]["browser_download_url"]
            require(unquote(url) == unquote(prefix) + name, f"Unexpected asset URL: {url}")
            return url, download(url)

        for filename in sorted(assets):
            generator = filename == "generator-build.json"
            if not generator and not (filename.startswith("stub-build-") and filename.endswith(".json")):
                continue
            _, manifest_data = asset(filename)
            manifest = json.loads(manifest_data)
            require(manifest["format_version"] == 1, f"Unsupported manifest: {filename}")
            native = manifest.get("environment", {})
            if generator:
                require(re.fullmatch(r"[0-9a-f]{40}", manifest["source_commit"]) is not None, "Invalid source commit")
            else:
                require("@sha256:" in native["image"], f"Image digest missing: {filename}")
            ubuntu_versions = sorted({image["ubuntu"] for image in manifest.get("images", [])
                                      if image["image"] == native.get("image")}) if not generator else []
            require(generator or not manifest.get("images") or len(ubuntu_versions) == 1,
                    f"Missing/ambiguous Ubuntu provenance: {filename}")
            for entry in manifest["wheels"]:
                require((entry["name"] == "gi-stub-gen") == generator, f"Wrong manifest for {entry['name']}")
                if not generator:
                    validate_native_labels(entry["version"], native)
                url, data = asset(entry["filename"])
                validate_wheel(entry, data)
                old = seen.get(entry["filename"])
                require(old is None or old["sha256"] == entry["sha256"], f"Conflicting wheel: {entry['filename']}")
                if old is not None:
                    old["ubuntu_versions"] = sorted(set(old["ubuntu_versions"]) | set(ubuntu_versions))
                    continue
                item = {**entry, "url": url, "environment": native, "release": tag,
                        "source_commit": manifest.get("source_commit"), "ubuntu_versions": ubuntu_versions.copy()}
                seen[entry["filename"]] = item
                catalog.append(item)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as directory:
        site = Path(directory) / "site"
        site.mkdir()
        _write_simple_index(site, catalog)
        ubuntu_links = []
        for ubuntu in UBUNTU_VERSIONS:
            entries = [entry for entry in catalog if entry["name"] == "gi-stub-gen"
                       or not entry["canonical"] and ubuntu in entry["ubuntu_versions"]]
            target = site / "ubuntu" / ubuntu
            _write_simple_index(target, entries)
            owner, project = repository.split("/")
            url = f"https://{owner}.github.io/{project}/ubuntu/{ubuntu}/simple/"
            command = f"python -m pip install --index-url {url} gi-gst-stubs"
            body = (f'<h1>Ubuntu {ubuntu} stub wheels</h1>'
                    '<p>This index contains native stub builds generated on this Ubuntu release and the shared generator. '
                    'It excludes recommended wheels without native suffixes and builds with unknown Ubuntu provenance. '
                    'Wheels remain universal for Python 3.12+; runtime libraries and bindings must be installed separately.</p>'
                    f'<pre><code>{html.escape(command)}</code></pre>'
                    '<p>Select this index without also adding the general index. '
                    'pip and uv do not detect your Ubuntu or native library versions.</p>'
                    '<p><a href="simple/">Simple index</a> · <a href="../../">All builds</a></p>')
            (target / "index.html").write_text(page(f"Ubuntu {ubuntu} GI stub wheels", body))
            ubuntu_links.append(f'<a href="ubuntu/{ubuntu}/">Ubuntu {ubuntu}</a> '
                                f'(<a href="ubuntu/{ubuntu}/simple/">Simple index</a>)')
        recommended = []
        for name in PACKAGES:
            entries = [entry for entry in catalog if entry["name"] == name and entry["canonical"]]
            if entries:
                entry = max(entries, key=lambda entry: Version(entry["version"]))
                recommended.append(f'"{entry["url"]}#sha256={entry["sha256"]}"')
        install = ('<pre><code>' + html.escape("python -m pip install \\\n    " + " \\\n    ".join(recommended))
                   + '</code></pre>') if recommended else '<p>No recommended wheels published yet.</p>'
        rows = []
        for entry in catalog:
            if entry["name"] == "gi-stub-gen":
                continue
            native = entry["environment"]
            values = [entry["name"], entry["version"], "Recommended" if entry["canonical"] else "Native build",
                      ", ".join(entry["ubuntu_versions"]) or "Unknown",
                      native["glib"], native["gtk"], native["gstreamer"], native["python"]]
            cells = "".join(f"<td>{html.escape(value)}</td>" for value in values)
            rows.append(f'<tr>{cells}<td><a href="{html.escape(entry["url"], quote=True)}">Wheel</a></td></tr>')
        generators = sorted((entry for entry in catalog if entry["name"] == "gi-stub-gen"),
                            key=lambda entry: Version(entry["version"]), reverse=True)
        generator_body = '<h2>Generator</h2><p>No generator release published yet.</p>'
        if generators:
            entry = generators[0]
            command = f'python -m pip install "{entry["url"]}#sha256={entry["sha256"]}"'
            generator_body = ('<h2>Generator</h2><p>Install in an environment with compatible PyGObject and native libraries. '
                              'For GStreamer, provide typelibs and Python overrides from your system, your own build, or the '
                              '<a href="https://matteo-bruni.github.io/gstreamer-oci/">gstreamer-oci binding indexes</a> '
                              '(select Ubuntu and pin the binding version to your native GStreamer).</p>'
                              f'<pre><code>{html.escape(command)}</code></pre>'
                              '<p>The generator does not require our gst-python-binding distribution. '
                              '<a href="simple/gi-stub-gen/">All generator versions</a>.</p>')
        body = ('<h1>GI generator and stub wheels</h1>' + generator_body +
                '<h2>Stub packages</h2><p>Type annotations for PyGObject, graphics, GStreamer and GTK. '
                'These packages do not install runtime bindings, native libraries or typelibs.</p>'
                '<p>All wheels are <code>py3-none-any</code> for Python 3.12+; no separate Ubuntu or Python ABI build is needed. '
                'The described APIs depend on the native libraries used during generation.</p>'
                '<h2>Ubuntu indexes</h2><p>For consumer projects, choose the index matching the generation environment: '
                + " · ".join(ubuntu_links) + '. These indexes contain native variants only; the general index remains complete.</p>'
                '<h2>Install recommended wheels</h2><p>Run in your project virtual environment; keep only the packages you need. '
                '<code>gi-base-stubs</code> covers core GI, <code>gi-graphics-core-stubs</code> graphics, '
                '<code>gi-gst-stubs</code> GStreamer and GES, and <code>gi-gtk-stubs</code> GTK.</p>'
                + install +
                '<p>For uv, replace <code>python -m pip install</code> with <code>uv pip install</code>.</p>'
                '<h2>Choose a native build</h2><p>Versions without <code>+</code> are recommended snapshots from the recent verified environment. '
                'Suffixes such as <code>+glib2.80</code> identify the native build environment, not a Python ABI requirement. '
                'Use its exact Wheel link below, or pin the full version from the <a href="simple/">Simple index</a>.</p>'
                '<p>pip and uv do not detect GLib or GTK. An unqualified install can prefer a local version; '
                '<code>==3.58.1</code> also matches <code>3.58.1+glib2.80</code>. '
                'The recommended commands use exact wheel URLs to avoid that ambiguity. '
                'A <code>.postN</code> suffix denotes a revised stub build.</p>'
                '<h2>Available wheels</h2>'
                '<table><thead><tr><th>Package</th><th>Version</th><th>Build</th><th>Ubuntu</th><th>GLib</th><th>GTK</th>'
                '<th>GStreamer</th><th>Build Python</th><th>Download</th></tr></thead><tbody>'
                + "\n".join(rows) + '</tbody></table>'
                '<p>Pages hosts static HTML only; wheels remain in GitHub Releases. '
                'The <a href="catalog.json">JSON catalog</a> records checksums and build provenance, including image digests.</p>'
                f'<p><a href="https://github.com/{html.escape(repository, quote=True)}">Source and documentation</a></p>')
        (site / "index.html").write_text(page("GI stub wheels", body))
        (site / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n")
        site.rename(output)
    return catalog


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(re.fullmatch(r"[\w.-]+/[\w.-]+", args.repository) is not None, "Expected owner/repository")
    result = subprocess.run(["gh", "api", "--paginate", "--slurp",
                             f"repos/{args.repository}/releases?per_page=100"], check=True, capture_output=True, text=True)
    releases = [release for batch in json.loads(result.stdout) for release in batch]
    catalog = write_index(args.repository, releases, args.output)
    print(f"Verified {len(catalog)} wheels in {args.output}")


if __name__ == "__main__":
    main()
