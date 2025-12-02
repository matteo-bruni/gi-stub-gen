import logging
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
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)

    stubs: dict[str, str] = {}
    # gather info for all modules in this stub package
    # we assume all modules share the same gi version
    for module_name in name:
        module = get_module_from_name(module_name=module_name, gi_version=gi_version)
        docs = gir_docs(Path(f"{gir_folder}/{module_name}-{gi_version}.gir"))

        parsed_module, unknown_module_map_types = parse_module(module, docs)
        stubs[module_name] = parsed_module.to_pyi(debug=debug)
        if unknown_module_map_types:
            logger.warning(
                f"Unknown/Not parsed elements for module {module_name}: {unknown_module_map_types}"
            )

    create_stub_package(
        root_folder=output,
        stubs=stubs,
        name=pkg_name,
        version=pkg_version,
        description=f"Type stubs for {name} GI module",
        author_name="Name Surname",
        author_email="author@example.com",
        min_python_version="3.12",
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
