"""Build immutable, universal release wheels from already generated stub packages."""

import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile

from packaging.version import Version
import tomlkit
from tomlkit.items import Table


PACKAGES = ("gi-base-stubs", "gi-graphics-core-stubs", "gi-gst-stubs", "gi-gtk-stubs")


def validate_native_labels(version: str, native: dict[str, str]) -> None:
    """Reject a cached native build mislabeled as the current environment."""
    for library in ("glib", "gtk", "cairo"):
        label = re.search(rf"(?:^|\.){library}(\d+\.\d+)(?:\.|$)", Version(version).local or "")
        if re.search(rf"(?:^|\.){library}", Version(version).local or "") and label is None:
            raise ValueError(f"Malformed native label: {version}; check the build dependencies")
        if label is not None and label[1] != native.get(library):
            raise ValueError(f"Native environment mismatch: {version}; regenerate against the selected libraries")


def environment(image: str) -> dict[str, str]:
    """Capture the native environment separately from Python wheel compatibility."""
    if "@sha256:" not in image:
        raise ValueError("Use an immutable image reference containing @sha256:")
    import gi
    import cairo

    gi.require_version("Gst", "1.0")
    gi.require_version("Gtk", "4.0")
    from gi.repository import GLib, Gst, Gtk

    Gst.init(None)
    return {
        "image": image, "python": platform.python_version(), "pygobject": version("PyGObject"),
        "glib": f"{GLib.MAJOR_VERSION}.{GLib.MINOR_VERSION}",
        "glib_runtime": f"{GLib.MAJOR_VERSION}.{GLib.MINOR_VERSION}.{GLib.MICRO_VERSION}",
        "gtk": f"{Gtk.MAJOR_VERSION}.{Gtk.MINOR_VERSION}",
        "cairo": ".".join(cairo.cairo_version_string().split(".")[:2]),
        "gstreamer": ".".join(map(str, Gst.version()[:3])),
    }


def release_versions(original: str, glib: str, canonical: bool, revision: int | None) -> list[str]:
    """Keep the native build identity and optionally add its public-version counterpart."""
    parsed = Version(original)
    if revision is not None and revision < 1:
        raise ValueError("Release revisions start at 1")
    public = f"{parsed.base_version}.post{revision}" if revision is not None else parsed.public
    versions = [f"{public}+{parsed.local or 'glib' + glib}"]
    if canonical:
        versions.append(public)
    return versions


def build_release(stubs: Path, output: Path, native: dict[str, str], *,
                  canonical: bool = False, revision: int | None = None) -> Path:
    """Rebuild metadata through the backend; never rename wheels or replace an output directory."""
    if output.exists():
        raise FileExistsError(f"Release output already exists: {output}; use a new output directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as directory:
        work = Path(directory)
        archives = work / "wheels"
        archives.mkdir()
        entries = []
        for name in PACKAGES:
            project = work / name
            shutil.copytree(stubs / name, project)
            config = project / "pyproject.toml"
            document = tomlkit.parse(config.read_text())
            project_info = document["project"]
            assert isinstance(project_info, Table)
            original = str(project_info["version"])
            validate_native_labels(original, native)
            library = "gstreamer" if name == "gi-gst-stubs" else "pygobject"
            if library in native and Version(original).base_version != Version(native[library]).base_version:
                raise ValueError(f"{name}: generated version does not match {library}; regenerate first")
            for version in release_versions(original, native["glib"], canonical, revision):
                project_info["version"] = version
                config.write_text(tomlkit.dumps(document))
                before = set(archives.glob("*.whl"))
                subprocess.run(["uv", "build", "--wheel", str(project), "--out-dir", str(archives)], check=True)
                added = set(archives.glob("*.whl")) - before
                if len(added) != 1:
                    raise ValueError(f"Expected one new wheel for {name} {version}")
                wheel = added.pop()
                if not wheel.name.endswith("-py3-none-any.whl"):
                    raise ValueError(f"Stub wheel is not universal: {wheel.name}")
                entries.append({
                    "filename": wheel.name, "name": name, "version": version,
                    "requires_python": str(project_info["requires-python"]),
                    "canonical": Version(version).local is None,
                    "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                })
        manifest = archives / f"stub-build-glib{native['glib']}.json"
        manifest.write_text(json.dumps({"format_version": 1, "environment": native, "wheels": entries}, indent=2) + "\n")
        archives.rename(output)
    return output / manifest.name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stubs", type=Path, default=Path("stubs"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", required=True, help="Image reference with its verified digest")
    parser.add_argument("--canonical", action="store_true", help="Also build public versions from this verified environment")
    parser.add_argument("--revision", type=int, help="Use .postN instead of replacing an existing release")
    args = parser.parse_args()
    print(build_release(args.stubs, args.output, environment(args.image), canonical=args.canonical, revision=args.revision))


if __name__ == "__main__":
    main()
