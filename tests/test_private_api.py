"""
These test check if the private API used are always available.
(private API can change between versions)

These are the minimal tests to ensure that the private API used in the
stub generator are still available.
"""

import gi._gi as GI  # type: ignore


def test_typetag():
    """
    Test if GI.TypeTag enum is available.
    We just check the Boolean typetag as representative.
    """
    assert hasattr(GI, "TypeTag")
    assert GI.TypeTag.BOOLEAN == 1


def test_typeinfo():
    """
    Test if GI.TypeInfo is available.
    """
    assert hasattr(GI, "TypeInfo")


def test_callbackinfo():
    """
    Test if GI.CallbackInfo is available.
    """
    assert hasattr(GI, "CallbackInfo")


def test_signalinfo():
    """
    Test if GI.SignalInfo is available.
    """
    assert hasattr(GI, "SignalInfo")


def test_functioninfo():
    """
    Test if GI.FunctionInfo is available.
    """
    assert hasattr(GI, "FunctionInfo")


def test_enuminfo():
    """
    Test if GI.EnumInfo is available.
    """
    assert hasattr(GI, "EnumInfo")


def test_valueinfo():
    """
    Test if GI.ValueInfo is available.
    """
    assert hasattr(GI, "ValueInfo")


def test_direction():
    """
    Test if GI.Directon enum is available.
    """
    assert hasattr(GI, "Direction")
    assert GI.Direction.IN == 0
    assert GI.Direction.OUT == 1
    assert GI.Direction.INOUT == 2
