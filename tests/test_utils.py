import pytest


@pytest.mark.parametrize(
    "name,expected_sane_name,expected_comment",
    [
        ("valid_name", "valid_name", None),
        (
            "1invalid-name",
            "_1invalid_name",
            "[1invalid-name]: changed because contained invalid characters, started with a number",
        ),
        ("class", "class_", "[class]: changed, name is a reserved keyword"),
        ("class!", "class_", "[class!]: changed because contained invalid characters"),
    ],
)
def test_sanitize_variable_name(
    name: str,
    expected_sane_name: str,
    expected_comment: str | None,
):
    from gi_stub_gen.utils.utils import sanitize_variable_name

    sane_variable, comment = sanitize_variable_name(name)
    assert sane_variable == expected_sane_name
    assert comment == expected_comment


def test_expected_failure_on_empty_name():
    from gi_stub_gen.utils.utils import sanitize_variable_name

    with pytest.raises(ValueError):
        sane_variable, comment = sanitize_variable_name(None)  # type: ignore
