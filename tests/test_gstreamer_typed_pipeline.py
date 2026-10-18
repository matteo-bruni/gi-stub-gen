from pathlib import Path
import subprocess
import sys


def test_typed_gstreamer_pipeline_runs():
    example = Path(__file__).resolve().parents[1] / "examples/gstreamer_typed_pipeline.py"
    result = subprocess.run([sys.executable, str(example)], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "buffer, probe, properties and EOS verified" in result.stdout
