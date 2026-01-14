"""
Tests for method_descriptor detection and override assumptions.

These tests verify our assumptions about PyGObject's internal structure,
specifically for methods implemented in C that are not introspectable via GI.
If these tests fail after a PyGObject upgrade, the overrides may need updating.
"""

import warnings

import pytest
from types import MethodDescriptorType

import gi

from gi.repository import GObject


class TestObjectMethodDescriptors:
    """Test that Object's method_descriptor methods exist and are correctly typed."""

    # Methods we expect to be method_descriptor on GObject.Object
    EXPECTED_METHOD_DESCRIPTORS = [
        "bind_property",
        "chain",
        "connect",
        "connect_after",
        "connect_object",
        "connect_object_after",
        "disconnect_by_func",
        "emit",
        "get_properties",
        "get_property",
        "handler_block_by_func",
        "handler_unblock_by_func",
        "set_properties",
        "set_property",
        "weak_ref",
    ]

    @pytest.mark.parametrize("method_name", EXPECTED_METHOD_DESCRIPTORS)
    def test_method_exists(self, method_name: str):
        """Verify method exists on GObject.Object."""
        assert hasattr(GObject.Object, method_name), (
            f"GObject.Object.{method_name} does not exist. PyGObject may have changed its API."
        )

    @pytest.mark.parametrize("method_name", EXPECTED_METHOD_DESCRIPTORS)
    def test_method_is_method_descriptor(self, method_name: str):
        """Verify method is a method_descriptor (C implementation)."""
        method = getattr(GObject.Object, method_name)
        assert type(method) is MethodDescriptorType, (
            f"GObject.Object.{method_name} is {type(method).__name__}, "
            f"expected method_descriptor. PyGObject implementation may have changed."
        )

    @pytest.mark.parametrize("method_name", EXPECTED_METHOD_DESCRIPTORS)
    def test_method_is_local_to_object(self, method_name: str):
        """Verify method is defined directly on Object, not inherited."""
        for klass in GObject.Object.__mro__:
            if method_name in klass.__dict__:
                assert klass.__name__ == "Object", (
                    f"GObject.Object.{method_name} is defined in {klass.__name__}, "
                    f"not Object. Inheritance structure may have changed."
                )
                return
        pytest.fail(f"GObject.Object.{method_name} not found in any class __dict__")


class TestGBoxedMethodDescriptors:
    """Test that GBoxed's method_descriptor methods exist and are correctly typed."""

    EXPECTED_METHOD_DESCRIPTORS = ["copy"]

    @pytest.mark.parametrize("method_name", EXPECTED_METHOD_DESCRIPTORS)
    def test_method_exists(self, method_name: str):
        """Verify method exists on GObject.GBoxed."""
        assert hasattr(GObject.GBoxed, method_name), (
            f"GObject.GBoxed.{method_name} does not exist. PyGObject may have changed its API."
        )

    @pytest.mark.parametrize("method_name", EXPECTED_METHOD_DESCRIPTORS)
    def test_method_is_method_descriptor(self, method_name: str):
        """Verify method is a method_descriptor (C implementation)."""
        method = getattr(GObject.GBoxed, method_name)
        assert type(method) is MethodDescriptorType, (
            f"GObject.GBoxed.{method_name} is {type(method).__name__}, "
            f"expected method_descriptor. PyGObject implementation may have changed."
        )

    @pytest.mark.parametrize("method_name", EXPECTED_METHOD_DESCRIPTORS)
    def test_method_is_local_to_gboxed(self, method_name: str):
        """Verify method is defined directly on GBoxed, not inherited."""
        for klass in GObject.GBoxed.__mro__:
            if method_name in klass.__dict__:
                assert klass.__name__ == "GBoxed", (
                    f"GObject.GBoxed.{method_name} is defined in {klass.__name__}, "
                    f"not GBoxed. Inheritance structure may have changed."
                )
                return
        pytest.fail(f"GObject.GBoxed.{method_name} not found in any class __dict__")


class TestGTypeStructure:
    """Test GType's structure and methods."""

    EXPECTED_PROPERTIES = [
        "name",
        "parent",
        "children",
        "depth",
        "fundamental",
        "interfaces",
        "pytype",
    ]

    EXPECTED_METHODS = [
        "from_name",
        "is_a",
        "is_abstract",
        "is_classed",
        "is_deep_derivable",
        "is_derivable",
        "is_instantiatable",
        "is_interface",
        "is_value_abstract",
        "is_value_type",
        "has_value_table",
    ]

    def test_gtype_exists(self):
        """Verify GType exists."""
        assert hasattr(GObject, "GType"), "GObject.GType does not exist"

    def test_gtype_is_type(self):
        """Verify GType is a type (metaclass)."""
        assert isinstance(GObject.GType, type), f"GObject.GType is {type(GObject.GType)}, expected type"

    @pytest.mark.parametrize("prop_name", EXPECTED_PROPERTIES)
    def test_gtype_property_exists(self, prop_name: str):
        """Verify GType property exists."""
        assert hasattr(GObject.GType, prop_name), (
            f"GObject.GType.{prop_name} does not exist. GType structure may have changed."
        )

    @pytest.mark.parametrize("method_name", EXPECTED_METHODS)
    def test_gtype_method_exists(self, method_name: str):
        """Verify GType method exists."""
        assert hasattr(GObject.GType, method_name), (
            f"GObject.GType.{method_name} does not exist. GType structure may have changed."
        )

    def test_gtype_from_name_works(self):
        """Verify GType.from_name actually works."""
        gtype = GObject.GType.from_name("GObject")
        assert gtype is not None
        assert gtype.name == "GObject"


class TestParamSpecStructure:
    """Test ParamSpec's structure for Fundamental type handling."""

    def test_paramspec_exists(self):
        """Verify ParamSpec exists."""
        assert hasattr(GObject, "ParamSpec"), "GObject.ParamSpec does not exist"

    def test_paramspec_is_fundamental(self):
        """Verify ParamSpec is a fundamental type (has no GI parent)."""
        # __info__ is an internal PyGObject attribute that may change
        # We check it exists but don't rely on it for public stubs
        if hasattr(GObject.ParamSpec, "__info__"):
            info = GObject.ParamSpec.__info__  # type: ignore[attr-defined]
            if hasattr(info, "get_fundamental"):
                assert info.get_fundamental() is True, (
                    "ParamSpec.get_fundamental() is not True. Type hierarchy may have changed."
                )

    def test_paramspec_mro_contains_fundamental(self):
        """Verify ParamSpec MRO contains gi.Fundamental."""
        mro_names = [cls.__name__ for cls in GObject.ParamSpec.__mro__]
        # Check that 'Fundamental' is in MRO (from gi module)
        # or that object is the direct parent
        has_fundamental = "Fundamental" in mro_names
        has_object_parent = GObject.ParamSpec.__mro__[1].__name__ in ("Fundamental", "object")
        assert has_fundamental or has_object_parent, (
            f"ParamSpec MRO is unexpected: {mro_names}. Fundamental type handling may need updating."
        )


class TestPropertyAlias:
    """Test Property alias structure."""

    def test_property_exists(self):
        """Verify Property class exists."""
        assert hasattr(GObject, "Property"), "GObject.Property does not exist"

    def test_property_alias_exists(self):
        """Verify property (lowercase) alias exists."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            assert hasattr(GObject, "property"), "GObject.property alias does not exist"

    def test_property_alias_equals_property(self):
        """Verify property alias points to Property."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            assert GObject.property is GObject.Property, (
                "GObject.property is not GObject.Property. Alias structure changed."
            )

    def test_property_alias_is_deprecated(self):
        """Verify property alias raises deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _ = GObject.property
            # Check if any deprecation warning was raised
            deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
            assert len(deprecation_warnings) > 0, (
                "GObject.property did not raise DeprecationWarning. Deprecation status may have changed."
            )


class TestOverridesConfiguration:
    """Test that our override configuration matches reality."""

    def test_object_overrides_exist(self):
        """Verify all Object method overrides reference existing methods."""
        from gi_stub_gen.overrides import CLASS_OVERRIDES

        object_overrides = CLASS_OVERRIDES.get("gi.repository.GObject", {}).get("Object", {})
        methods = object_overrides.get("methods", {})

        for method_name, override in methods.items():
            if override is not None:  # None means "remove method"
                assert hasattr(GObject.Object, method_name), (
                    f"Override exists for GObject.Object.{method_name} but method does not exist at runtime."
                )

    def test_gtype_overrides_exist(self):
        """Verify all GType overrides reference existing attributes."""
        from gi_stub_gen.overrides import CLASS_OVERRIDES

        gtype_overrides = CLASS_OVERRIDES.get("gi.repository.GObject", {}).get("GType", {})

        for field_name in gtype_overrides.get("fields", {}).keys():
            assert hasattr(GObject.GType, field_name), (
                f"Field override exists for GObject.GType.{field_name} but attribute does not exist at runtime."
            )

        for method_name, override in gtype_overrides.get("methods", {}).items():
            if override is not None:
                assert hasattr(GObject.GType, method_name), (
                    f"Method override exists for GObject.GType.{method_name} but method does not exist at runtime."
                )

    def test_gboxed_overrides_exist(self):
        """Verify all GBoxed method overrides reference existing methods."""
        from gi_stub_gen.overrides import CLASS_OVERRIDES

        gboxed_overrides = CLASS_OVERRIDES.get("gi.repository.GObject", {}).get("GBoxed", {})
        methods = gboxed_overrides.get("methods", {})

        for method_name, override in methods.items():
            if override is not None:
                assert hasattr(GObject.GBoxed, method_name), (
                    f"Override exists for GObject.GBoxed.{method_name} but method does not exist at runtime."
                )


class TestMethodDescriptorParsing:
    """Test the method_descriptor parsing logic."""

    def test_method_descriptor_type_detection(self):
        """Verify MethodDescriptorType correctly identifies method_descriptors."""
        method = GObject.Object.connect
        assert type(method) is MethodDescriptorType

    def test_method_descriptor_not_introspectable(self):
        """Verify method_descriptors are not in GI introspection."""
        gi.require_version("GIRepository", "3.0")
        from gi.repository import GIRepository

        repo = GIRepository.Repository()
        repo.require("GObject", "2.0", GIRepository.RepositoryLoadFlags.NONE)

        object_info = repo.find_by_name("GObject", "Object")
        gi_methods = set()
        # Note: get_n_methods/get_method exist at runtime but may not be in stubs
        for i in range(object_info.get_n_methods()):  # type: ignore[attr-defined]
            method = object_info.get_method(i)  # type: ignore[attr-defined]
            gi_methods.add(method.get_name())

        # These should NOT be in GI introspection
        not_in_gi = [
            "chain",
            "connect_after",
            "connect_object",
            "connect_object_after",
            "disconnect_by_func",
            "get_properties",
            "handler_block_by_func",
            "handler_unblock_by_func",
            "set_properties",
        ]

        for method_name in not_in_gi:
            assert method_name not in gi_methods, (
                f"{method_name} is now in GI introspection! Override may no longer be needed."
            )
