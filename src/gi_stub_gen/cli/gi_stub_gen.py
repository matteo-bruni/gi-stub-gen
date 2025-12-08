# Copyright (c) 2025 Matteo Bruni

import logging
from typing import Literal

from rich.logging import RichHandler
from pathlib import Path


import typer
from typing_extensions import Annotated

from gi_stub_gen.manager import TemplateManager


app = typer.Typer(pretty_exceptions_enable=False)
logger = logging.getLogger(__name__)


@app.command()
def main(
    name: Annotated[
        list[str],
        typer.Argument(
            help="List of module names to generate stubs for. The syntax is <module_name>:<gi_version>  if gi_version is needed to load the module.",
        ),
    ],
    pkg_name: Annotated[
        str,
        typer.Option(
            help="Stub Package name. Ideally match the library name. "
            "(i.e PyGobject-stubs for gi and GObject, "
            "Gstreamer-stubs for Gst, GstVideo, etc...)"
        ),
    ],
    pkg_version: Annotated[
        str,
        typer.Option(
            help="Stub Package version. Ideally match the library version. "
            "(i.e PyGobject version for gi and GObject, "
            "Gstreamer version for Gst, GstVideo, etc...)"
        ),
    ],
    preload: Annotated[
        list[str] | None,
        typer.Option(
            help="List of module names to preload before generating stubs. The syntax is <module_name>:<gi_version>  if gi_version is needed to load the module. Note: this will not generate stubs for these modules.",
        ),
    ] = None,
    pkg_author: Annotated[
        str,
        typer.Option(
            help="Stub Package author name.",
        ),
    ] = "Name Surname",
    pkg_author_email: Annotated[
        str,
        typer.Option(
            help="Stub Package author email.",
        ),
    ] = "author@example.com",
    pkg_description: Annotated[
        str,
        typer.Option(
            help="Stub Package description.",
        ),
    ] = "Type stubs for GI libraries",
    pkg_min_python_version: Annotated[
        str,
        typer.Option(
            help="Minimum Python version required by the stub package.",
        ),
    ] = "3.10",
    pkg_dependencies: Annotated[
        list[str],
        typer.Option(
            help="List of dependencies for the stub package.",
        ),
    ] = [],
    stub_gi_include: Annotated[
        list[str],
        typer.Option(
            help="List of additional gi.repository.<module_name> to include in the stubs. "
            "The syntax is <module_stub>:<gi_module_to_include>."
            "(i.e Gio:GioUnix to include gi.repository.GioUnix in the Gio stubs).",
        ),
    ] = [],
    debug: Annotated[
        bool,
        typer.Option("--debug", "-d", help="Enable debug mode"),
    ] = False,
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output folder where to save the generated stub package",
            dir_okay=True,
        ),
    ] = Path("stubs"),
    gir_folder: Annotated[
        Path,
        typer.Option(
            "--gir-folder",
            "-g",
            help="Path to the folder containing the .gir files",
            dir_okay=True,
        ),
    ] = Path("/usr/share/gir-1.0/"),
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            "-w",
            help="Overwrite existing files in the output folder",
        ),
    ] = False,
    log_level: Annotated[
        Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        typer.Option(
            help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        ),
    ] = "INFO",
):
    # setup logging
    logging.basicConfig(
        # level=logging.ERROR,
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(show_path=debug)],
    )

    from gi_stub_gen.utils import get_gi_module_from_name, split_gi_name_version

    logger.info(f"Generating stub package for modules: {name}")
    # preload all modules to avoid runtime gi.require_version issues
    # some modules require other modules to be loaded first
    module_to_preload = preload + name if preload is not None else name
    for n in module_to_preload:
        module_name, gi_version = split_gi_name_version(n)

        logger.info(f"Preloading module {module_name} gi_version={gi_version}")
        m = get_gi_module_from_name(module_name=module_name, gi_version=gi_version)

        # special cases for modules that need init called
        if module_name == "Gst":
            m.init(None)

    from gi_stub_gen.package import create_stub_package
    from gi_stub_gen.parser.module import parse_module
    from gi_stub_gen.parser.gir import gir_docs

    # get extra import to add to each stub file
    extra_include_per_stub: dict[str, list[str]] = {}
    for s in stub_gi_include:
        if ":" not in s or len(s.split(":")) != 2:
            logger.error(
                f"Invalid stub_gi_include format: {s}. Expected format is <module_stub>:<gi_module_to_include>"
            )
            continue
        module_stub, gi_module_to_include = s.split(":")
        if module_stub not in extra_include_per_stub:
            extra_include_per_stub[module_stub] = []
        extra_include_per_stub[module_stub].append(gi_module_to_include)

    stubs: dict[str, str] = {}
    unknown: dict[str, dict[str, list[str]]] = {}
    # gather info for all modules in this stub package
    # we assume all modules share the same gi version
    for n in name:
        module_name, gi_version = split_gi_name_version(n)

        module = get_gi_module_from_name(module_name=module_name, gi_version=gi_version)
        docs = gir_docs(Path(f"{gir_folder}/{module_name}-{gi_version}.gir"))

        parsed_module, unknown_module_map_types = parse_module(
            module, docs, debug=debug
        )
        unknown[module_name] = unknown_module_map_types
        stub_file_name = module_name
        # if stub_file_name == "gi":
        #     stub_file_name = "__init__"
        stubs[stub_file_name] = parsed_module.to_pyi(
            extra_gi_repository_import=extra_include_per_stub.get(module_name, []),
            debug=debug,
            unknowns=unknown_module_map_types,
        )

    total_unknown = sum(
        len(attributes)
        for unknown_module_map_types in unknown.values()
        for attributes in unknown_module_map_types.values()
    )
    logger.warning("#" * 80)
    logger.warning(f"# Unknown/Not parsed elements: {total_unknown}")
    logger.warning("#" * 80)
    for module_name, unknown_module_map_types in unknown.items():
        if len(unknown_module_map_types) > 0:
            logger.warning(f"##### Module {module_name} #####")

        for unknown_key, attributes in unknown_module_map_types.items():
            logger.warning(f"- {unknown_key}")
            for attribute in attributes:
                logger.warning(f"    {module_name}.{unknown_key}: {attribute}")

    create_stub_package(
        root_folder=output,
        stubs=stubs,
        name=pkg_name,
        version=pkg_version,
        description=pkg_description,
        author_name=pkg_author,
        author_email=pkg_author_email,
        min_python_version=pkg_min_python_version,
        overwrite=overwrite,
        dependencies=pkg_dependencies,
    )

    logger.info(f"Stub Package generated for {pkg_name} in {output}")
