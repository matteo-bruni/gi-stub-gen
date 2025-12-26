from gi_stub_gen.manager.gir_docs import GIRDocs
from gi_stub_gen.parser.gir import translate_docstring


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


MessageType_EXTENDED = """
    Message is an extended message type (see below).
        These extended message IDs can't be used directly with mask-based API
        like gst_bus_poll() or gst_bus_timed_pop_filtered(), but you can still
        filter for GST_MESSAGE_EXTENDED and then check the result for the
        specific type. (Since: 1.4)
    """

GstBus = """
    The GstBus provides support for #GSource based notifications. This makes it
    possible to handle the delivery in the glib #GMainLoop.

    The #GSource callback function gst_bus_async_signal_func() can be used to
    convert all bus messages into signal emissions.

    A message is posted on the bus with the gst_bus_post() method. With the
    gst_bus_peek() and gst_bus_pop() methods one can look at or retrieve a
    previously posted message.

    The bus can be polled with the gst_bus_poll() method. This methods blocks
    up to the specified timeout value until one of the specified messages types
    is posted on the bus. The application can then gst_bus_pop() the messages
    from the bus to handle them.
    Alternatively the application can register an asynchronous bus function
    using gst_bus_add_watch_full() or gst_bus_add_watch(). This function will
    install a #GSource in the default glib main loop and will deliver messages
    a short while after they have been posted. Note that the main loop should
    be running for the asynchronous callbacks.
"""