# Python API

Full API reference can be generated from docstrings via the Sphinx docs build.

Use a simple import path for quick tasks, or construct richer workflows in code.

## One-liner

```python
from pyptmpl import __version__

print(__version__)
```

## Advanced

```python
from importlib import import_module

pkg = import_module("pyptmpl")
print(pkg.__name__)
```
