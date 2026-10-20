from gi.repository import GObject, Gst

from gi_stub_gen.overrides.class_.Gst.Element import transform_register
from gi_stub_gen.parser.class_ import parse_class
from gi_stub_gen.parser.function import parse_function
from gi_stub_gen.schema.function import FunctionSchema


def test_element_registration_preserves_metadata_and_still_needs_correction():
    original = parse_function(Gst.Element.register, None)
    assert original is not None
    argument = next(arg for arg in original.args if arg.name == "type")
    assert argument.render_type_annotation("Gst", for_input=True) == "GObject.GType", (
        "Uncorrected Gst.Element.register input changed; review/remove transform_register"
    )
    corrected = transform_register(original.model_copy(deep=True))
    assert isinstance(corrected, FunctionSchema)
    assert corrected.model_dump(exclude={"args"}) == original.model_dump(exclude={"args"})
    assert corrected.args[:-1] == original.args[:-1]
    assert corrected.args[-1].render_type_annotation("Gst", for_input=True) == "GObject.GType | type[Element]"
    assert argument.input_type_name is None

    schema, _ = parse_class("gi.repository.Gst", Gst.Element)
    assert schema is not None
    register = next(method for method in schema.methods if method.name == "register")
    assert register.args[-1].render_type_annotation("Gst", for_input=True) == "GObject.GType | type[Element]"


def test_register_accepts_an_element_class_and_native_gtype():
    class Probe(Gst.Bin):
        __gtype_name__ = "GiStubGenElementRegistrationProbe"
        __gstmetadata__ = ("Probe", "Generic/Bin", "Registration test", "Test")

    name = "gi-stub-gen-element-registration-probe"
    assert Gst.Element.register(None, name, Gst.Rank.NONE, Probe)
    factory = Gst.ElementFactory.find(name)
    assert factory is not None
    gtype = GObject.type_from_name("GiStubGenElementRegistrationProbe")
    assert factory.get_element_type() == gtype
    assert Gst.Element.register(None, name, Gst.Rank.NONE, gtype)
