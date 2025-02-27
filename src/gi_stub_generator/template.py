# _build(m, args.module, overrides)
# m=Gst, module=Gst as string,
# build(parent: ObjectT, namespace: str, overrides: dict[str, str])
# Gst, Gst:str, dir(Gst)


# print(dir(Gst))

TEMPLATE = """from typing import Any
from typing import Callable
from typing import Literal
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Type
from typing import TypeVar

import gi
import gi._gi as GI
from gi.repository import GLib
from gi.repository import GObject

##############################################################
# Enums/Flags
##############################################################

{% for e in enums -%}
{% if e.namespace == module -%}
class {{e.name}}({{e.py_super_type_str}}):
    {%- if e.docstring %}
    \"\"\"
    {{e.docstring['class']}}
    \"\"\"

    {% endif -%}
    {% for f in e.fields -%}
    {{f.name}} = {{f.value_repr}}
    {% if e.docstring %}\"\"\"{{e.docstring[f.name|lower]}}\"\"\"{% endif %}
    {% endfor %}
{% else -%}
{{e.name}} = {{e.namespace}}.{{e.name}}
{% endif %}
{% endfor %}

##############################################################
# Constants
##############################################################

{% for c in constants -%}
{{c.name}}: {{c.type_repr}} = {{c.value_repr}}
{% endfor %}


##############################################################
# Functions
##############################################################

{% for f in functions -%}
def {{f.name}}(
    {% for a in f.input_args -%}
    {{a.name}}: {{a.type_repr}},
    {% endfor -%}
) -> {{f.return_repr}}:
    {%- if f.docstring %}
    \"\"\"
    {{f.docstring}}
    \"\"\"
    {% endif -%}
    ...

{% endfor %}

"""
