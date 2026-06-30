import gi

gi.require_version("Pango", "1.0")

from gi.repository import Pango

from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.parser.class_ import parse_class


def test_font_map_list_families_returns_typed_list():
    parsed_class, _ = parse_class("Pango", Pango.FontMap)
    assert parsed_class is not None

    list_families = next(method for method in parsed_class.methods if method.name == "list_families")
    assert list_families.complete_return_hint("Pango") == "list[FontFamily]"

    TemplateManager.set_module_name("Pango")
    rendered = parsed_class.render()
    assert "def list_families(self) -> list[FontFamily]:" in rendered
