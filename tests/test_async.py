import ast
import subprocess
import sys

import gi._gi as GI
from gi.repository import Gio

from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.parser.function import parse_function


def test_async_overloads_preserve_explicit_none_and_finish_result():
    parsed = parse_function(Gio.InputStream.read_bytes_async, "Preserved documentation")
    assert parsed is not None and len(parsed.overloads) == 3
    awaited, positional, keyword = parsed.overloads
    assert awaited.render_return_annotation("Gio") == "gi._gi.Async[GLib.Bytes]"
    assert [arg.name for arg in awaited.args] == ["count", "io_priority", "cancellable"]
    assert positional.args[-2].is_required
    assert positional.args[-2].may_be_null
    assert keyword.args[-1].is_keyword_only and keyword.args[-1].is_required
    TemplateManager.set_module_name("Gio")
    text = parsed.render_stub_compact()
    tree = ast.parse(text, feature_version=(3, 12))
    assert len(tree.body) == 3
    assert all(isinstance(node, ast.FunctionDef) for node in tree.body)
    assert text.count("Preserved documentation") == 1
    assert "callback=None" not in text.replace(" ", "")


def test_async_uses_finish_metadata_including_non_async_suffix():
    runtime = Gio.File.mount_enclosing_volume
    assert isinstance(runtime, GI.FunctionInfo)
    assert runtime.get_finish_func() is not None
    parsed = parse_function(runtime, None)
    assert parsed is not None and parsed.overloads
    finish = parse_function(Gio.File.mount_enclosing_volume_finish, None)
    assert finish is not None
    assert parsed.overloads[0].return_hint == f"Async[{finish.render_return_annotation('Gio')}]"
    ordinary = parse_function(Gio.File.get_path, None)
    assert ordinary is not None and not ordinary.overloads
    constructor = parse_function(Gio.DBusConnection.new_for_address, None)
    assert constructor is not None and not constructor.overloads


def test_async_and_probe_marshalling_in_fresh_process():
    # Isolate GLib's loop policy and callback registrations from the rest of the suite.
    code = """
import asyncio
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gio, GLib, Gst
from gi.events import GLibEventLoopPolicy
from gi import _gi
Gst.init(None)
for values in [(), (42,), (42, "label")]:
    pad = Gst.Pad.new("probe", Gst.PadDirection.SRC)
    seen = []
    def probe(source, info, *data):
        assert source == pad
        seen.append(data)
        return Gst.PadProbeReturn.REMOVE
    pad.add_probe(Gst.PadProbeType.IDLE, probe, *values)
    assert seen == [values]

def stream():
    return Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(b"abc"))

async def run():
    task = stream().read_bytes_async(3, GLib.PRIORITY_DEFAULT, None)
    assert isinstance(task, _gi.Async)
    assert isinstance(task.cancellable, Gio.Cancellable)
    done = []
    task.add_done_callback(lambda result: done.append(result.result().get_data()))
    assert (await task).get_data() == b"abc"
    await asyncio.sleep(0)
    assert task.done() and task.exception() is None and task.result().get_data() == b"abc"
    assert done == [b"abc"]
    assert stream().read_bytes_async(3, 0, callback=None) is None
    assert stream().read_bytes_async(3, 0, None, None) is None
    for values in [(), (42,), (42, "label")]:
        completed = asyncio.get_running_loop().create_future()
        def callback(source, result, *data):
            assert data == values
            completed.set_result(source.read_bytes_finish(result).get_data())
        assert stream().read_bytes_async(3, 0, None, callback, *values) is None
        assert await completed == b"abc"
    cancel = Gio.Cancellable()
    cancel.cancel()
    task = stream().read_bytes_async(3, 0, cancel)
    assert task.cancel() is None
    try:
        await task
    except GLib.Error:
        assert isinstance(task.exception(), GLib.Error)
    else:
        raise AssertionError("Expected cancellation")

policy = GLibEventLoopPolicy()
asyncio.set_event_loop_policy(policy)
loop = policy.get_event_loop()
try:
    loop.run_until_complete(run())
finally:
    loop.close()
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
