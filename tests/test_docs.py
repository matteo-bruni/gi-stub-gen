from gi_stub_gen.gir_manager import GIRDocs


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
