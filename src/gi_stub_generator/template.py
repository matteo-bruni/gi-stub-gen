TEMPLATE = """from __future__ import annotations
import typing
from typing_extensions import deprecated
import types
import pkgutil # needed by gi
import gi
import gi._gi as GI # type: ignore
import _thread
from gi.repository import GLib
from gi.repository import GObject

##############################################################
# Enums/Flags
##############################################################

{% for e in enums -%}
{% if e.namespace == module -%}
{% if debug -%}
\"\"\"
{{e.debug}}
\"\"\"
{% endif -%}
class {{e.name}}({{e.py_super_type_str}}):
    {% if e.docstring -%}
    \"\"\"
    {{e.docstring}}
    \"\"\"

    {% endif %}

    {%- for f in e.fields -%}
    {{f.name}} = {{f.value_repr}}
    {%- if f.docstring %}
    \"\"\"{{f.docstring}}\"\"\"
    {% endif %}
    {% endfor %}
{% else -%}
{{e.name}} = {{e.namespace}}.{{e.name}}
{% endif %}
{% endfor %}

##############################################################
# Constants
##############################################################

{% for c in constants -%}
{% if c.is_enum_or_flags -%}
{{c.name}} = {{c.value_repr}}
{% else -%}
{{c.name}}: {{c.type_repr}} = {{c.value_repr}}
{% endif -%}
{% if debug -%}
\"\"\"
{{c.debug}}
\"\"\"
{% elif c.docstring -%}
\"\"\"
{{c.docstring}}
\"\"\"
{% endif -%}
{% endfor %}


##############################################################
# Functions
##############################################################

{% for f in functions -%}
def {{f.name}}(
    {% for a in f.input_args -%}
    {{a.name}}: {{a.type_hint}},
    {% endfor -%}
) -> {{f.complete_return_hint}}:
    {% if debug -%}
    \"\"\"
    {{f.debug}}
    \"\"\"
    {% elif f.docstring -%} 
    \"\"\"
    {{f.docstring.docstring}}

    {%- if f.docstring.params %}

    Args:
    {%- for param, param_doc in f.docstring.params.items() %}
        {{param}}: {{param_doc}}
    {%- endfor %}
    {%- endif -%}

    {%- if f.docstring.return_doc %}

    Returns:
        {{f.docstring.return_doc}}
    {% endif %}
    \"\"\"
    {% endif -%}
    ...

{% endfor %}

##############################################################
# builtin_functions
##############################################################

{% for f in builtin_function -%}
{% if f.is_async %}async{% endif %}def {{f.name}}(
    {% for a in f.param_signature -%}
    {{a}},
    {% endfor -%}
) -> {{f.return_hint}}:
    {% if debug -%}
    \"\"\"
    {{f.debug}}
    \"\"\"
    {% elif f.docstring -%}
    \"\"\"
    {{f.docstring}}
    \"\"\"
    {% endif -%}
    ...
{% endfor %}

##############################################################
# classes
##############################################################

{% for c in classes -%}
class {{c.name}}({{','.join(c.super)}}):
    {% if debug -%}
    \"\"\"
    {{c.debug}}
    \"\"\"
    {% elif c.docstring and c.docstring.class_docstring -%}
    \"\"\"
    {{c.docstring.class_docstring}}
    \"\"\"
    {% endif -%}

    {% if c.props -%}
    class Props:
        {% for p in c.props %}
        {% if p.is_deprecated -%}
        @deprecated(reason="TODO??")
        {% endif -%}
        {{p.name}}: {{p.type_repr}} {% if p.line_comment %}{{ p.line_comment }}{% endif %}
        {%- endfor %}
        
    props: Props = ...
    {% endif -%}

    ...

{% endfor %}


##############################################################
# Callbacks
##############################################################

{% for cb in callbacks -%}
class {{cb.name}}(typing.Protocol):
    {% if debug -%}
    \"\"\"
    {{cb.debug}}
    \"\"\"
    {% elif cb.docstring -%}
    \"\"\"
    {{cb.docstring}}
    \"\"\"
    {% endif -%}

    def __call__(
        self,
        {% for a in cb.function.input_args -%}
        {{a.name}}: {{a.type_hint}},
        {% endfor -%}
    ) -> {{cb.function.complete_return_hint}}:
        ...
    ...
{% endfor %}


##############################################################
# Aliases
##############################################################

{% for a in aliases -%}
{{a.name}} = {{a.target_repr}} {% if a.line_comment %}{{ a.line_comment }}{% endif %}
{% if a.docstring -%}
\"\"\"
{{a.docstring}}
\"\"\"
{% endif -%}
{% endfor %}

"""
