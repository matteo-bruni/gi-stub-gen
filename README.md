# start developing

```
uv sync
source .venv/bin/activate
```

note this need pygobject that need pygobject and pycairo.
in order to install pygobject (and pycairo) (does not have precompiled wheels) you need on ubuntu:

```
sudo apt install build-essential python3-dev libcairo2-dev libgirepository-1.0-dev libgirepository-2.0-dev
```

```
gi_stub_gen  > test.pyi
```


# why not from gir?

gir files are missing all the helpers functions defined by pygobject and from the libraries overrides.
If lib overrides are installed, they will be included in the output.

Gir files are used if available to obtain the docstrings since i didnt find a way to get them from the introspection 
data through pygobject.