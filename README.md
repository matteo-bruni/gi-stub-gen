
A stub generator for GObject Introspection (GI) libraries.
The types are discovered using importing the libraries from `gi.repository`.

### Why ?

started developing with gstreamer python binding and found the lack of type hints quite annoying. Additionally looking at the existing `pygobject-stubs` i found quite difficult to understand and contribute to it, so decided to start a new project.

The `pygobject-stubs` project while a neat project was quite difficult to understand and contribute to for someone not familiar with the GI internals. There is not separation between the parsing and the template generation, making it difficult to extend or fix issues. Also the generated stubs collect all the libraries in a single monolithic package. Instead i prefer to have a separate package for each library, so that is possible to install only the needed stubs and maybe the stubs for a particular library can be maintained by the library maintainers. Also from my understanding a lot the stubs are manually fixed, which is not very maintainable.
The focus of this project is to split the parsing and the template generation, so that is possible to extend or fix issues more easily. When parsing all the information is collected in Pydantic models, that can be easily inspected or modified before generating the stubs. Also the generated stubs are separated in different packages, one for each library. In my idea there will be a base package `gi-base-stub` that will contain the common stubs for all the libraries (like `GObject`, `GLib`, etc...) and then a package for each library that will depend on the base package.
In the first development phase the generated stubs will be uploaded in `stubs/` folder, but maybe in the future they can be uploaded to PyPI or another package index.

feature:
- dont like to pick the version at runtime for each library, just publish stubs for each version and install the needed one.
- try to catch pydeprecation warnings for aliases and attributes and add to their docstring
- try to add deprecated decorator to deprecated functions and methods
- do not manually fix the generated stubs, try to improve the generator instead.
- signal
- gerror


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

## stub folder
the generated stub in `stubs/` folder are generated using the `build-all.sh` script.
These can be seen as examples of the generated stubs. 
Ideally these can be published to PyPI or another package index in the future.
In my idea each project should maintain the stubs for their own library, and link the stub version to the library version.


## problem with GIRepository for parsing
i found some issues with GIRepository when parsing some libraries, for example:
- gi._gi.FunctionInfo is mapped to GIRepository.FunctionInfo. However GIRepository.FunctionInfo does not have all the methods that gi._gi.FunctionInfo has. For example gi._gi.FunctionInfo has get_arguments() (added by pygobject) but in GIRepository.FunctionInfo it is missing and is showing the C counterpart get_n_args() and get_args() which are not directly usable in Python.
- in GIRepository.TypeInfo there is no method get_tag_as_string, while gi._gi.TypeInfo has get_tag_as_string() added by pygobject

## disclaimer
i'm by no means an expert in GI or pygobject, so there might be some mistakes or misunderstandings in the generated stubs.
i started this project mainly to learn more about GI and pygobject internals, so any feedback or contribution is welcome.

## todo 

- add more tests
- better parse the gir files
- create build system to use docker files to get consistent build environment