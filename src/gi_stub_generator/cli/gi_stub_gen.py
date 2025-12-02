import logging

from rich.logging import RichHandler
from pathlib import Path

from gi_stub_generator.package import create_stub_package
from gi_stub_generator.parser.module import parse_module
from gi_stub_generator.parser.gir import gir_docs

import typer
from typing_extensions import Annotated

from gi_stub_generator.utils import get_module_from_name


app = typer.Typer(pretty_exceptions_enable=False)
logger = logging.getLogger(__name__)


@app.command()
def main(
    name: list[str],
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
            help="Minimum Python version required for the stub package.",
        ),
    ] = "3.12",
    gi_version: Annotated[
        str | None,
        typer.Option(help="GI Library version"),
    ] = None,
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
):
    # setup logging
    handler = RichHandler()
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[handler],
    )

    stubs: dict[str, str] = {}
    unknown: dict[str, dict[str, list[str]]] = {}
    # gather info for all modules in this stub package
    # we assume all modules share the same gi version
    for module_name in name:
        module = get_module_from_name(module_name=module_name, gi_version=gi_version)
        docs = gir_docs(Path(f"{gir_folder}/{module_name}-{gi_version}.gir"))

        parsed_module, unknown_module_map_types = parse_module(module, docs)
        stubs[module_name] = parsed_module.to_pyi(debug=debug)
        unknown[module_name] = unknown_module_map_types
        # if unknown_module_map_types:
        #     logger.warning(
        #         f"Unknown/Not parsed elements for module {module_name}: {unknown_module_map_types}"
        #     )

    logger.warning("#" * 80)
    logger.warning("# Unknown/Not parsed elements")
    logger.warning("#" * 80)
    for module_name, unknown_module_map_types in unknown.items():
        if len(unknown_module_map_types) > 0:
            logger.warning(f"##### Module {module_name} #####")

        for unknown_key, attributes in unknown_module_map_types.items():
            logger.warning(f"\t- {unknown_key}")
            for attribute in attributes:
                logger.warning(f"\t\t{module_name}.{unknown_key}: {attribute}")

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
    )

    logger.info(f"Stub Package generated for {pkg_name} in {output}")

    # print("#" * 80)
    # print("# Unknown/Not parsed elements")
    # print("#" * 80)
    # for key, value in unknown_module_map_types.items():
    #     print(f"- {key=}: \n{value=}")
    #     print("\n")
    # return

    # print("#" * 80)
    # print("# constants")
    # print("#" * 80)
    # for f in data.constant:
    #     print(f)
