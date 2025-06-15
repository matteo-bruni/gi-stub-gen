import logging
import gi
import jinja2
import importlib
from pathlib import Path

from gi_stub_generator.create import check_module
from gi_stub_generator.gir_parser import gir_docs
from gi_stub_generator.template import TEMPLATE

import typer
from typing_extensions import Annotated

from gi_stub_generator.utils import get_module_from_name


app = typer.Typer(pretty_exceptions_enable=False)
logger = logging.getLogger(__name__)


@app.command()
def main(
    name: str,
    version: Annotated[str | None, typer.Option(help="Library version")] = None,
    debug: Annotated[
        bool, typer.Option("--debug", "-d", help="Enable debug mode")
    ] = False,
    # output: Annotated[
    #     str | None, typer.Option("--output", "-o", help="Output file path")
    # ] = "gi_stub.py",
):
    # setup logging
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)

    module = get_module_from_name(name, version)
    docs = gir_docs(Path(f"/usr/share/gir-1.0/{name}-{version}.gir"))

    data, unknown_module_map_types = check_module(module, docs)
    # data, unknown_module_map_types = check_module(Gst)
    environment = jinja2.Environment()
    output = environment.from_string(TEMPLATE)

    with open(f"{name}_stub.pyi", "w") as f:
        f.write(
            output.render(
                module=module.__name__.split(".")[-1],
                constants=data.constant,
                enums=data.enum,
                functions=data.function,
                classes=data.classes,
                debug=debug,
                aliases=data.aliases,
            )
        )

    logger.info(f"Stub file generated for {name} at {name}_stub.pyi")

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
