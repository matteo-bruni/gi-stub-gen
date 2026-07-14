from gi_stub_gen.schema.class_ import ClassFieldSchema, ClassSchema


def _make_enum_meta_schema(name: str, runtime_name: str) -> ClassSchema:
    return ClassSchema(
        namespace="GObject",
        name=name,
        super=["enum.EnumType", "GType"],
        docstring=(
            f"Stub-only static typing model of gi._enum.{runtime_name}. "
            "EnumType models the runtime enum behavior; GType models "
            "PyGObject's implicit acceptance of enum classes in GType parameters."
        ),
        line_comment=f"Typing-only model of gi._enum.{runtime_name}; not a public PyGObject runtime API.",
        props=[],
        required_gi_import="enum",
        fields=[
            ClassFieldSchema(
                name="__gtype__",
                type_hint_name="GType",
                type_hint_namespace="GObject",
                may_be_null=False,
                line_comment=None,
                is_deprecated=False,
                deprecation_warnings=None,
                docstring="The GType associated with the enum class.",
                is_readable=True,
                is_writable=False,
            ),
        ],
        methods=[],
        python_methods=[],
        signals=[],
        extra=[],
        is_deprecated=False,
    )


GENUM_META_SCHEMA = _make_enum_meta_schema("_GEnumMeta", "GEnumMeta")
GFLAGS_META_SCHEMA = _make_enum_meta_schema("_GFlagsMeta", "GFlagsMeta")
