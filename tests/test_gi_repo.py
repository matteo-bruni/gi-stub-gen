from typing import assert_type

import pytest
from gi.repository import GIRepository

from gi_stub_gen.manager.gi_repo import GIRepo


def test_lookup_overloads_preserve_optional_and_positional_arguments():
    repo = GIRepo()
    repo.require("GObject", "2.0")
    plain = repo.find_by_name("GObject", "Object")
    explicit = repo.find_by_name("GObject", "Object", target_type=None)
    keyword = repo.find_by_name("GObject", "Object", target_type=GIRepository.ObjectInfo)
    positional = repo.find_by_name("GObject", "Object", "2.0", GIRepository.ObjectInfo)
    assert_type(plain, GIRepository.BaseInfo | None)
    assert_type(explicit, GIRepository.BaseInfo | None)
    assert_type(keyword, GIRepository.ObjectInfo | None)
    assert_type(positional, GIRepository.ObjectInfo | None)
    for info in (plain, explicit, keyword, positional):
        assert isinstance(info, GIRepository.ObjectInfo)
        assert info.get_name() == "Object"
    assert repo.find_by_name("GObject", "NotAnExistingType") is None
    with pytest.raises(TypeError, match="Expected GObject.Object to be FunctionInfo"):
        repo.find_by_name("GObject", "Object", target_type=GIRepository.FunctionInfo)
