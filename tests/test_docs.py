from unittest.mock import Mock
from gi_stub_gen.manager.gi_repo import GIRepo
from gi_stub_gen.manager.gir_docs import GIRDocs
from gi_stub_gen.parser.gir import parse_gir_docs
from gi_stub_gen.utils.gir_docs import translate_docstring


def test_singleton_behavior():
    doc1 = GIRDocs()
    doc2 = GIRDocs()
    assert doc1 is doc2
    assert id(doc1) == id(doc2)


def test_load_gir_success(fake_gir_file):
    docs = GIRDocs()
    success = docs.load(fake_gir_file)

    assert success is True
    assert docs._gir_path == fake_gir_file


def test_load_gir_not_found():
    docs = GIRDocs()
    import pathlib

    success = docs.load(pathlib.Path("/path/to/nothing.gir"))

    assert success is False


def test_get_function_docstring(fake_gir_file):
    GIRDocs().load(fake_gir_file)

    doc = GIRDocs().get_function_docstring("hello_world")
    assert doc is not None
    assert "Prints hello" in doc


def test_get_constant_docstring(fake_gir_file):
    """Verifica il recupero della docstring di una costante."""
    GIRDocs().load(fake_gir_file)

    doc = GIRDocs().get_constant_docs("MY_CONSTANT")

    assert doc == "A magic number."


def test_reset_works(fake_gir_file):
    GIRDocs().load(fake_gir_file)
    assert GIRDocs().get_function_docstring("hello_world") is not None

    # 2. Resetta
    GIRDocs.reset()

    # 3. Verifica che sia vuoto (nota: GIRDocs() crea una nuova istanza vuota)
    assert GIRDocs().get_function_docstring("hello_world") is None


def test_callable_c_type_metadata_is_extracted(tmp_path):
    gir_file = tmp_path / "TestLib-1.0.gir"
    gir_file.write_text(
        """<?xml version="1.0"?>
<repository version="1.2" xmlns="http://www.gtk.org/introspection/core/1.0" xmlns:c="http://www.gtk.org/introspection/c/1.0" xmlns:glib="http://www.gtk.org/introspection/glib/1.0">
  <namespace name="TestLib" version="1.0">
    <function name="marshal_values" c:identifier="test_marshal_values">
      <return-value transfer-ownership="full"><type name="GObject.Value" c:type="GValue*"/></return-value>
      <parameters>
        <parameter name="source" transfer-ownership="none"><type name="GObject.Value" c:type="const GValue*"/></parameter>
        <parameter name="destination" transfer-ownership="none"><type name="GObject.Value" c:type="GValue*"/></parameter>
        <parameter name="values" transfer-ownership="none"><array c:type="const GValue*"><type name="GObject.Value" c:type="GValue"/></array></parameter>
      </parameters>
    </function>
    <callback name="ValueCallback" c:type="TestValueCallback">
      <return-value transfer-ownership="none"><array c:type="const GValue*"><type name="GObject.Value" c:type="GValue"/></array></return-value>
      <parameters><parameter name="value" transfer-ownership="none"><type name="GObject.Value" c:type="GValue*"/></parameter></parameters>
    </callback>
    <class name="Sample" c:type="TestSample">
      <method name="method"><return-value transfer-ownership="none"><type name="none" c:type="void"/></return-value><parameters><parameter name="value"><type name="GObject.Value" c:type="const GValue*"/></parameter></parameters></method>
      <constructor name="new"><return-value transfer-ownership="full"><type name="Sample" c:type="TestSample*"/></return-value></constructor>
      <glib:signal name="changed" when="last"><return-value transfer-ownership="none"><type name="GObject.Value" c:type="GValue*"/></return-value></glib:signal>
    </class>
  </namespace>
</repository>
""",
        encoding="utf-8",
    )

    docs = parse_gir_docs(gir_file)
    assert docs is not None
    function = docs.functions["marshal_values"]
    assert function.param_types["source"].c_type == "const GValue*"
    assert function.param_types["destination"].c_type == "GValue*"
    assert function.param_types["values"].c_type == "const GValue*"
    assert function.param_types["values"].element_c_type == "GValue"
    assert function.param_types["values"].is_array is True
    assert function.return_type is not None
    assert function.return_type.transfer_ownership == "full"
    assert docs.callbacks["ValueCallback"].param_types["value"].c_type == "GValue*"
    assert docs.callbacks["ValueCallback"].return_type is not None
    assert docs.callbacks["ValueCallback"].return_type.is_array is True
    assert docs.classes["Sample"].methods["method"].param_types["value"].c_type == "const GValue*"
    assert docs.classes["Sample"].methods["new"].return_type is not None
    assert docs.classes["Sample"].methods["new"].return_type.c_type == "TestSample*"
    assert docs.classes["Sample"].signals["changed"].return_type is not None
    assert docs.classes["Sample"].signals["changed"].return_type.c_type == "GValue*"


def test_translate_c_to_py_docstring_complex_scenario():
    namespace = "Gst"

    # 1. C Function: gst_element_link()
    # 2. Param: @src
    # 3. Values: NULL, TRUE, FALSE
    # 4. Class: #GstBin
    # 5. Constant: %GST_STATE_PLAYING
    # 6. XML: &lt;tag&gt;
    # 7. Backslash (Path Windows): C:\Windows\System32
    # 8. Triple Quotes: """

    raw_doc = (
        "Use gst_element_link() to connect @src.\n"
        "Returns %TRUE if linked, %FALSE if @src is NULL.\n"
        "See #GstBin for details on state %GST_STATE_PLAYING.\n"
        "Supports XML tags like &lt;video&gt;.\n"
        "Warning: paths like C:\\Windows\\System32 must be escaped.\n"
        'Never use unescaped """triple quotes""".'
    )

    # Expected translated docstring
    expected_doc = (
        "Use `Gst.element_link` to connect `src`.\n"
        "Returns True if linked, False if `src` is None.\n"
        "See Gst.Bin for details on state Gst.STATE_PLAYING.\n"
        "Supports XML tags like <video>.\n"
        "Warning: paths like C:\\\\Windows\\\\System32 must be escaped.\n"
        'Never use unescaped \\"\\"\\"triple quotes\\"\\"\\".'
    )

    result = translate_docstring(raw_doc, namespace)
    assert result == expected_doc, f"\nExpected:\n{expected_doc}\n\nGot:\n{result}"


def test_empty_docstring():
    assert translate_docstring(None, "Gst") == ""
    assert translate_docstring("", "Gst") == ""


def test_translate_docstring_smart_class_resolution():
    """
    Tests the heuristic logic that converts C function calls (snake_case)
    into Python method calls (CamelCase class + method) by looking up
    classes in a mocked GIRepository.
    """

    namespace = "Gst"
    version = "1.0"

    repo = GIRepo()
    repo.require(namespace, version)

    # INPUT:
    # 1. Bus (Semplice) -> Gst.Bus
    # 2. Bin (Semplice) -> Gst.Bin
    # 3. TypeFindFactory (Multi-parola) -> Gst.TypeFindFactory
    #    (Sostituisce AppSink che sta in GstApp)
    # 4. Init (Funzione Globale) -> Gst.init

    raw_doc = (
        "Use gst_bus_post() msg.\n"
        "Call gst_bin_add().\n"
        "Advanced: use gst_type_find_factory_get_list().\n"
        "Global gst_init()."
    )

    # OUTPUT ATTESO:
    expected_doc = (
        "Use `Gst.Bus.post` msg.\n"
        "Call `Gst.Bin.add`.\n"
        "Advanced: use `Gst.TypeFindFactory.get_list`.\n"
        "Global `Gst.init`."
    )

    # --- 4. Execution ---
    # We pass the mock_repo explicitly to the function
    result = translate_docstring(raw_doc, namespace, repo=repo)
    # result = translate_docstring(raw_doc, namespace, repo=mock_repo)

    # --- 5. Assertion ---
    # In pytest, we simply use the `assert` keyword.
    # If it fails, pytest provides a detailed diff.
    assert result == expected_doc, f"\nExpected:\n{expected_doc}\n\nGot:\n{result}"
