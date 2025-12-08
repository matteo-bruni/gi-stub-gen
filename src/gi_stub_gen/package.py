import logging
import shutil
import tomlkit
from pathlib import Path

logger = logging.getLogger(__name__)


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
        current_version: str = pyproject_toml["project"]["version"]  # pyright: ignore[reportIndexIssue, reportAssignmentType]

        logger.info(
            f"File {folder / 'pyproject.toml'} already exists with version {current_version}."
        )
        # ask user if they want to overwrite
        response = input(f"Do you want to overwrite it with version {version}? [y/N]: ")
        if response.lower() != "y":
            logger.info("Aborting package creation.")
            return

    author_entry = f'{{ name = "{author_name}", email = "{author_email}" }}'
    pyproject_template = f"""
[project]
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
        f.write(pyproject_template)

    # check if readme exists
    if not (folder / "README.md").exists():
        readme_template = f"# {name}\n\nAdd your project description here."
        with open(folder / "README.md", "w") as f:
            f.write(readme_template)

    package_folder = folder / "src" / "gi-stubs" / "repository"
    if not package_folder.exists():
        package_folder.mkdir(parents=True)
    elif overwrite:
        logger.info(f"Overwriting existing package folder at {package_folder}")
        # remove all files in the package folder
        shutil.rmtree(package_folder)
        package_folder.mkdir(parents=True)

    for stub_name, stub_content in stubs.items():
        logger.info(
            f"Creating stub file for {stub_name} at {package_folder / f'{stub_name}.pyi'}"
        )
        with open(package_folder / f"{stub_name}.pyi", "w") as f:
            f.write(stub_content)
