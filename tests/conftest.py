import pytest


# from gi.repository import GIRepository  # noqa: E402
from gi.repository import Gst
import pytest
from pathlib import Path

from gi_stub_gen.gir_manager import GIRDocs


@pytest.fixture(scope="session", autouse=True)
def init_gst():
    """
    Initialize GStreamer for tests that need it.
    """
    print("Initializing GStreamer...")
    Gst.init(None)
    return


# Contenuto minimo di un file GIR per i test
FAKE_GIR_CONTENT = """<?xml version="1.0"?>
<repository version="1.2" xmlns="http://www.gtk.org/introspection/core/1.0" xmlns:c="http://www.gtk.org/introspection/c/1.0" xmlns:glib="http://www.gtk.org/introspection/glib/1.0">
  <namespace name="TestLib" version="1.0" shared-library="libtest.so" c:identifier-prefixes="Test" c:symbol-prefixes="test">
    
    <function name="hello_world" c:identifier="test_hello_world">
      <doc xml:space="preserve" filename="test.c" line="10">Prints hello to stdout.</doc>
      <return-value transfer-ownership="none">
        <type name="none" c:type="void"/>
      </return-value>
    </function>

    <constant name="MY_CONSTANT" value="42" c:type="TEST_MY_CONSTANT">
      <doc xml:space="preserve" filename="test.c" line="20">A magic number.</doc>
      <type name="gint" c:type="gint"/>
    </constant>

  </namespace>
</repository>
"""


@pytest.fixture
def fake_gir_file(tmp_path):
    """
    Crea un file .gir temporaneo e restituisce il percorso (Path).
    Viene distrutto automaticamente alla fine del test.
    """
    gir_file = tmp_path / "TestLib-1.0.gir"
    gir_file.write_text(FAKE_GIR_CONTENT, encoding="utf-8")
    return gir_file


@pytest.fixture(autouse=True)
def reset_gir_docs():
    GIRDocs.reset()
    yield  # here the test runs
    GIRDocs.reset()
