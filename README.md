
A stub generator for GObject Introspection (GI) libraries.
The types are discovered using importing the libraries from `gi.repository`.

### Why ?
The `pygobject-stubs` project while a neat project was quite difficult to understand and contribute to for someone not familiar with the GI internals. There is not separation between the parsing and the template generation, making it difficult to extend or fix issues. Also the generated stubs collect all the libraries in a single monolithic package. Instead i prefer to have a separate package for each library, so that is possible to install only the needed stubs and maybe the stubs for a particular library can be maintained by the library maintainers. Also from my understanding a lot the stubs are manually fixed, which is not very maintainable.
The focus of this project is to split the parsing and the template generation, so that is possible to extend or fix issues more easily. When parsing all the information is collected in Pydantic models, that can be easily inspected or modified before generating the stubs. Also the generated stubs are separated in different packages, one for each library. In my idea there will be a base package `gi-base-stub` that will contain the common stubs for all the libraries (like `GObject`, `GLib`, etc...) and then a package for each library that will depend on the base package.
In the first development phase the generated stubs will be uploaded in `stubs/` folder, but maybe in the future they can be uploaded to PyPI or another package index.

feature:
- dont like to pick the version at runtime for each library, just publish stubs for each version and install the needed one.
- try to catch pydeprecation warnings for aliases and attributes and add to their docstring
- try to add deprecated decorator to deprecated functions and methods


### Why not from gir files?

Generating the stubs importing the libraries from `gi.repository` allows to:
 - discover what is actually available in the library, without the need to search for the updated gir files.
 - discover the overrides defined by the libraries, since the gir files do not include them.


### Docstring

Gir files are used to obtain the docstrings since they are not available from the introspection data through pygobject at the time of writing this library.

# Develop

install the dependencies:
```
uv sync
source .venv/bin/activate
```

**note:** this need pygobject that need pygobject and pycairo.
in order to install pygobject (and pycairo) (does not have precompiled wheels) you need on ubuntu:

```
sudo apt install \
  build-essential \
  python3-dev \
  libcairo2-dev \
  libgirepository-1.0-dev \
  libgirepository-2.0-dev
```

TODO CHANGEME
```
gi_stub_gen <library_name> <gi_version> > test.pyi
```


# TODO
- [ ] Add support for deprecated function and methods
- [ ] Add support Classes
- [ ] Add support Classes attributes
- [ ] Add support for GType constant
- [ ] Add tests
- [ ] Auto add import for other gi.repository modules used in type hints



# possibile bug
ndr magari quando si fanno alias va tutto

in GObject.DestroyNotifyCB

in realtà è 
DestroyNotifyCB = GLib.DestroyNotifyCB

ma in funzione 

def signal_add_emission_hook(
    signal_id: int,
    detail: int,
    hook_func: SignalEmissionHookCB,
    hook_data: object | None,
    data_destroy: DestroyNotifyCB | None,
) -> int:

dice che 
{
          "namespace": "GObject",
          "name": "data_destroy",
          "is_optional": false,
          "direction": "IN",
          "is_callback": true,
          "may_be_null": true,
          "is_deprecated": false,
          "tag_as_string": "interface",
          "get_array_length": -1,
          "py_type_name": "DestroyNotifyCB",
          "py_type_namespace": null,
          "line_comment": null
        }

sembra di GObject e non di Glib?