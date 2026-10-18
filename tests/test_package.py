from pathlib import Path

from gi_stub_gen.package import create_stub_package


def test_root_distribution_owns_partial_package_markers(tmp_path: Path):
    stubs = {"gi": "", "gi.repository.Gio": "class File: ...\n"}
    for _ in range(2):
        create_stub_package(tmp_path, "base", stubs, "0.0.1", "Test package", "Test", overwrite=True)
        package = tmp_path / "base/src/gi-stubs"
        assert (package / "repository/__init__.pyi").read_text() == ""
        assert (package / "py.typed").read_text() == "partial\n"

    assert set(stubs) == {"gi", "gi.repository.Gio"}

    create_stub_package(
        tmp_path,
        "addon",
        {"gi.repository.Gst": "class Element: ...\n"},
        "0.0.1",
        "Test package",
        "Test",
        overwrite=True,
    )
    addon = tmp_path / "addon/src/gi-stubs"
    assert (addon / "repository/Gst.pyi").is_file()
    assert not (addon / "repository/__init__.pyi").exists()
    assert not (addon / "py.typed").exists()


def test_overwrite_removes_obsolete_stubs_but_preserves_markers(tmp_path: Path):
    stubs = {"gi": "", "gi.repository.Obsolete": "class Obsolete: ...\n"}
    create_stub_package(tmp_path, "base", stubs, "0.0.1", "Test", "Test", overwrite=True)
    create_stub_package(tmp_path, "base", {"gi": ""}, "0.0.2", "Test", "Test", overwrite=True)
    package = tmp_path / "base/src/gi-stubs"
    assert not (package / "repository/Obsolete.pyi").exists()
    assert (package / "repository/__init__.pyi").is_file()
    assert (package / "py.typed").read_text() == "partial\n"
