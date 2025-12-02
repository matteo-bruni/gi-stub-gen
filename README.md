# possible names:

| Name       | Available on PyPI | Description                     |
|------------|-------------------|---------------------------------|
| stibby     | ✔                 | A playful stub generator name. |
| stubgi     | ✔                 | Stub generator for GI bindings.|
| zoji       | ✔                 | 🛠️ Come “Starcraft” o “Minecraft” → per costruire mondi di tipi.      |
| stubcraft  | ✔                 | Crafting stubs with precision. |
| sutajii    | ✔                 | da “stub” e “G” (ジー), abbreviato, stile tecnico.   |
| stubzilla  | ✔                 | A powerful stub generator.     |
| ghosttype  | ✔                 | Riferimento a "ghost types" o “ghosting” del codice: gli stub sono "fantasmi" delle vere librerie. Invisible typing assistance.   |
| typoid     | ✔                 | 🧬 Come un “droid”, ma per i tipi → sintetico e nerd. |
| gstubby    | ✔                 | 🧙‍♂️ Sembra un nome fantasy (come “Stubby il nano”), ma con “G” per GObject.    |
| stubulus   | ✔                 | 🧠 Riferimento a Stimulus → stimola i type checker!

  |

A stub generator for GObject Introspection (GI) libraries.
The types are discovered using importing the libraries from `gi.repository`.

### Why not from gir files?

Generating the stubs importing the libraries from `gi.repository` allows to:
 - discover what is actually available in the library, without the need to search for the updated gir files.
 - discover the overrides defined by the libraries, since the gir files do not include them.

### Docstring

Gir files are used to obtain the docstrings since they are not available from the introspection data through pygobject.

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
- [ ] Add support for deprecated
- [X] Fix the issue with the `Error` class being duplicated in the module (Error and GError)
- [ ] Add Callbacks via Protocol
- [ ] Add support for `gi._gi`
- [ ] Add support Classes
- [ ] Add support for GType constant
- [ ] Rename
- [ ] Add tests

