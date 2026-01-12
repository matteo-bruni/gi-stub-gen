import logging
import re
import tomlkit
from pathlib import Path

from gi_stub_gen.utils.utils import format_stub_with_ruff

logger = logging.getLogger(__name__)


# Regex to match the Date line in the stub header
# Example: "Date: 2024-01-11"
_DATE_LINE_PATTERN = re.compile(r"^Date:\s*\d{4}-\d{2}-\d{2}\s*$", re.MULTILINE)


def _normalize_stub_content(content: str) -> str:
    """
    Normalize stub content by removing the Date line.
    This allows comparing stubs ignoring only the generation date.
    """
    return _DATE_LINE_PATTERN.sub("Date: <NORMALIZED>", content)


def _should_write_stub(existing_path: Path, new_content: str) -> bool:
    """
    Check if we should write the stub file.
    Returns True if the file doesn't exist or if the content has changed
    (ignoring the Date line in the header).
    """
    if not existing_path.exists():
        return True

    try:
        existing_content = existing_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        logger.warning(f"Could not read existing stub {existing_path}: {e}")
        return True

    # Compare normalized versions (without date)
    normalized_existing = _normalize_stub_content(existing_content)
    normalized_new = _normalize_stub_content(new_content)

    return normalized_existing != normalized_new


def create_stub_package(
    root_folder: Path,
    name: str,
    stubs: dict[str, str],  # file_name -> stub_content
    version: str,
    description: str,
    author_name: str,
    author_email: str = "",
    min_python_version: str = "3.12",
    overwrite: bool = False,
    dependencies: list[str] | None = None,
):
    folder = root_folder / name
    if not folder.exists():
        folder.mkdir(parents=True)

    if not folder.is_dir():
        raise ValueError(f"Provided path {folder} is not a directory")

    pyproject_toml_path = folder / "pyproject.toml"
    if pyproject_toml_path.exists() and not overwrite:
        pyproject_toml = tomlkit.loads(pyproject_toml_path.read_text(encoding="utf-8"))
        current_version: str = pyproject_toml["project"]["version"]  # type: ignore

        logger.info(f"File {folder / 'pyproject.toml'} already exists with version {current_version}.")
        # ask user if they want to overwrite
        response = input(f"Do you want to overwrite it with version {version}? [y/N]: ")
        if response.lower() != "y":
            logger.info("Aborting package creation.")
            return

    author_entry = f'{{ name = "{author_name}", email = "{author_email}" }}'
    pyproject_template = f"""[project]
name = "{name}"
version = "{version}"
description = "{description}"
readme = "README.md"
authors = [
    {author_entry}
]
requires-python = ">={min_python_version}"
dependencies = [{", ".join(f'"{dep}"' for dep in (dependencies or []))}]
keywords = ["types", "stub", "gi", "gobject", "introspection"]
classifiers = [
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Typing :: Typed",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/gi-stubs"]"""

    with open(pyproject_toml_path, "w") as f:
        f.write(format_stub_with_ruff(pyproject_template, virtual_filename="pyproject.toml"))

    # check if readme exists
    if not (folder / "README.md").exists():
        readme_template = f"# {name}\n\nAdd your project description here."
        with open(folder / "README.md", "w") as f:
            f.write(readme_template)

    package_folder = folder / "src" / "gi-stubs"
    if not package_folder.exists():
        package_folder.mkdir(parents=True)
    # Note: we no longer delete the folder on overwrite.
    # Instead, we compare content and only write files that have actually changed.
    # This avoids unnecessary file modifications when only the date differs.

    # gi -> package_folder/__init__.pyi
    # gi.repository.<module> -> package_folder/repository/<module>.pyi
    # gi.<module> -> package_folder/repository/<module>.pyi
    skipped_count = 0
    written_count = 0
    generated_paths: set[Path] = set()  # Track all paths we're generating

    for stub_name, stub_content in stubs.items():
        # if / "repository"

        if stub_name == "gi":
            pyi_path = package_folder / "__init__.pyi"
        else:
            stub_subpath = stub_name.removeprefix("gi.").split(".")
            stub_folder = stub_subpath[:-1]
            stub_file = stub_subpath[-1]
            pyi_path = package_folder / Path(*stub_folder) / f"{stub_file}.pyi"
            pyi_path.parent.mkdir(parents=True, exist_ok=True)

        generated_paths.add(pyi_path)

        # Check if we should write the stub (content changed, ignoring date)
        if _should_write_stub(pyi_path, stub_content):
            logger.info(f"Writing stub file for {stub_name} at {pyi_path}")
            with open(pyi_path, "w") as f:
                f.write(stub_content)
            written_count += 1
        else:
            logger.debug(f"Skipping {stub_name}: no changes detected (only date differs)")
            skipped_count += 1

    # If overwrite is enabled, remove any .pyi files that are no longer being generated
    removed_count = 0
    if overwrite and package_folder.exists():
        for existing_pyi in package_folder.rglob("*.pyi"):
            if existing_pyi not in generated_paths:
                logger.info(f"Removing obsolete stub: {existing_pyi}")
                existing_pyi.unlink()
                removed_count += 1

    if skipped_count > 0:
        logger.info(f"Skipped {skipped_count} stub(s) with no changes (only date differs)")
    if written_count > 0:
        logger.info(f"Wrote {written_count} stub(s) with changes")
    if removed_count > 0:
        logger.info(f"Removed {removed_count} obsolete stub(s)")
