import gi
import jinja2
import importlib
from pathlib import Path
from gi_stub_generator.create import check_module
from gi_stub_generator.gir_parser import gir_docs
from gi_stub_generator.template import TEMPLATE

import typer
from typing_extensions import Annotated


app = typer.Typer()


@app.command()
def main(
    name: str,
    version: Annotated[str, typer.Argument()] = "1.0",
):
    gi.require_version(name, version)
    module = importlib.import_module(f".{name}", "gi.repository")
    docs = gir_docs(Path(f"/usr/share/gir-1.0/{name}-{version}.gir"))

    data, unknown_module_map_types = check_module(module, docs)
    # data, unknown_module_map_types = check_module(Gst)
    environment = jinja2.Environment()
    output = environment.from_string(TEMPLATE)

    print(
        output.render(
            module=module.__name__.split(".")[-1],
            constants=data.constant,
            enums=data.enum,
            functions=data.function,
            classes=data.classes,
        )
    )

    # print("#" * 80)
    # print("# Unknown/Not parsed elements")
    # print("#" * 80)
    # for key, value in unknown_module_map_types.items():
    #     print(f"- {key=}: \n{value=}")
    #     print("\n")
    # # return

    # print("#" * 80)
    # print("# constants")
    # print("#" * 80)
    # for f in data.constant:
    #     print(f)
