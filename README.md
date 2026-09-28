# Griffe Extensions for frequenz-core

[![Build Status](https://github.com/frequenz-floss/griffe-frequenz-core/actions/workflows/ci.yaml/badge.svg)](https://github.com/frequenz-floss/griffe-frequenz-core/actions/workflows/ci.yaml)
[![PyPI Package](https://img.shields.io/pypi/v/griffe-frequenz-core)](https://pypi.org/project/griffe-frequenz-core/)
[![Docs](https://img.shields.io/badge/docs-latest-informational)](https://frequenz-floss.github.io/griffe-frequenz-core/)

## Introduction

This package provides [Griffe](https://mkdocstrings.github.io/griffe/)
extensions that help [mkdocstrings](https://mkdocstrings.github.io/) understand
some helpers from
[`frequenz-core`](https://github.com/frequenz-floss/frequenz-core-python).

Some of these helpers use patterns that Griffe can't fully understand by just
reading the source code. This means that some information might be missing from
the generated API documentation.

The extensions fill in these gaps. The first one handles deprecations:
`frequenz-core` can deprecate APIs using function calls instead of decorators.
Neither Griffe's built-in support for `@deprecated` nor
[`griffe-warnings-deprecated`](https://mkdocstrings.github.io/griffe-warnings-deprecated/)
can detect these calls.

The extensions recognize helpers by their fully qualified names, without
importing `frequenz-core`. So you don't need `frequenz-core` as a dependency,
and you can use the extensions to document any project that uses these helpers.

## Installation

Add `griffe-frequenz-core` to your documentation dependencies, alongside
`mkdocstrings`.

Then enable the extensions you want in the `extensions` option of the
mkdocstrings Python handler, as shown below.

## Documenting deprecations

The `griffe_frequenz_core.deprecations` extension finds deprecations made using
`frequenz-core` helper functions.

It works alongside `griffe-warnings-deprecated`, which handles deprecations
made using decorators. You can enable both:

```yaml
plugins:
  - mkdocstrings:
      handlers:
        python:
          options:
            extensions:
              - griffe_warnings_deprecated
              - griffe_frequenz_core.deprecations
```

By default, both extensions use the same format, so all deprecations look the
same in your documentation.

For each deprecated object, the extension:

- Adds a `deprecated` label.
- Stores the deprecation notice in the object's `deprecated` field.
- Adds an admonition with the notice at the top of its docstring.

The notices follow the [deprecations
guide](https://github.com/frequenz-floss/docs/blob/v0.x.x/python/deprecations.md).

A warning shown at runtime is different from a notice in the documentation. The
runtime warning needs to identify the deprecated object. In the documentation,
readers already know which object they're looking at.

So a documentation notice should simply say **since which version** the object
is deprecated and **what to use instead**, with a link to the replacement.

The extension tries to build this notice from the arguments passed to the
helper. If you need a different notice, you can write one yourself using a
`Deprecated:` section in the docstring. A hand-written notice always takes
priority.

If you use a different admonition style for deprecations, you can change the
`kind` option. For example:

```yaml
plugins:
  - mkdocstrings:
      handlers:
        python:
          options:
            extensions:
              - griffe_warnings_deprecated:
                  kind: deprecated
              - griffe_frequenz_core.deprecations:
                  kind: deprecated
```

### Recognized frequenz-core helpers

The extension currently understands these helpers:

| `frequenz-core` helper                        | How it's used                        | What gets documented     |
|-----------------------------------------------|--------------------------------------|--------------------------|
| `frequenz.core.warnings.deprecated_aliases()` | Assigned to a module's `__getattr__` | All aliases in the table |
| `frequenz.core.warnings.DeprecatedAlias`      | An entry in that table               | The alias                |
| `frequenz.core.enum.deprecated_member()`      | Used as an enum member's value       | The enum member          |
| `frequenz.core.enum.DeprecatedMember`         | Used as an enum member's value       | The enum member          |

Griffe resolves imports before matching these names, so aliases work too. For
example, this is recognized:

```python
from frequenz.core.enum import deprecated_member as dm
```

### Deprecated module aliases

When you move or rename something, you might want to keep the old name working
for a while.

The `deprecated_aliases()` helper lets you do this by setting a module's
`__getattr__`. You can also declare the old names under `TYPE_CHECKING`, so
type checkers can still find them.

Each old name is described by a `DeprecatedAlias` entry. You can provide:

- `new_module`: The module where the object lives now.
- `new_name`: Its new name, if it was renamed.
- `since`: The version where the old name became deprecated.
- `message`: A custom runtime warning, instead of `since`.

You need to provide `new_module`, `new_name` or both, and exactly one of
`since` and `message`.

For example:

```python
from typing import TYPE_CHECKING, TypeAlias

from frequenz.core.warnings import DeprecatedAlias, deprecated_aliases

if TYPE_CHECKING:
    from mypkg.newmod import Gadget as _Gadget
    from mypkg.newmod import Widget as _Widget

    Widget: TypeAlias = _Widget
    """A widget that does widget things."""

    Doohickey: TypeAlias = _Gadget
    """A gadget, formerly known as `Doohickey`."""
else:
    __getattr__ = deprecated_aliases(
        __name__,
        DeprecatedAlias("Widget", new_module="mypkg.newmod", since="v1.2.0"),
        DeprecatedAlias(
            "Doohickey", new_module="mypkg.newmod", new_name="Gadget", since="v1.3.0"
        ),
        DeprecatedAlias("Thingamajig", new_name="Widget", since="v1.4.0"),
    )
```

Suppose this code is in `mypkg.oldmod`. Here's what happens in the generated
documentation:

- **`Widget`** gets the notice "Deprecated since v1.2.0. Use
  `mypkg.newmod.Widget` instead." The replacement is linked, and its value is
  shown as `mypkg.newmod.Widget` instead of the private `_Widget`.
- **`Doohickey`** points to `mypkg.newmod.Gadget`, because both the module and
  the name changed.
- **`Thingamajig`** points to `mypkg.oldmod.Widget`, because only the name
  changed. Its notice says "Use `Widget` instead.", with a link to that name.

A few other things worth knowing:

- **You don't need a `TYPE_CHECKING` declaration for every alias.** The
  extension marks all aliases as deprecated. If a name isn't declared under
  `TYPE_CHECKING`, it creates a module attribute for it, so the alias still
  appears in the documentation.
- **You can customize the notice using `default_message`.** The extension
  replaces `{since}` with the version string exactly as provided. The notice
  appears next to the alias in the documentation, so it doesn't repeat the
  deprecated name. It links the replacement using code formatting.
- **The `message` argument only affects runtime warnings.** It doesn't change
  the documentation notice. If an entry has a `message` instead of `since`, the
  notice only says what to use instead. To say more, write a `Deprecated:`
  section in the docstring under `TYPE_CHECKING`.
- **Replacement links use normal cross-references.** If a link can't be
  resolved, `mkdocs-autorefs` reports it. For replacements in another project,
  add that project's `objects.inv` URL to the Python handler's `inventories`.
- **Each alias is processed separately.** If the extension can't read one
  entry, it skips that entry and continues with the others. Arguments such as
  `category` and `stacklevel` don't affect the documentation.
- **The helper must be assigned directly to `__getattr__`.** A custom `def
  __getattr__()` that calls `deprecated_aliases()` internally won't be
  recognized. Neither will a `__getattr__` created in some other way.

### Deprecated enum members

You can deprecate an enum member by wrapping its value with
`deprecated_member()` or `DeprecatedMember`, giving the message for the runtime
warning.

For example:

```python
from frequenz.core.enum import DeprecatedMember, Enum, deprecated_member


class TaskStatus(Enum):
    OPEN = 1
    PENDING = deprecated_member(1, "PENDING is deprecated, use OPEN instead")
    WAITING = DeprecatedMember(1, "WAITING is deprecated, use OPEN instead")
```

The extension marks both members using their message as written. It also shows
their actual value instead of the wrapper. For example, the documentation shows
`PENDING = 1`, not the call to `deprecated_member()`.

### Hand-written admonitions

Sometimes the generated notice isn't enough. For example, you might want to
explain how to migrate to a new API or link to a migration guide.

You can do this by adding a deprecation admonition to the object's docstring.

If the extension finds one, it leaves the docstring as it is, instead of adding
another admonition. It still adds the `deprecated` label and fills in the
`deprecated` field.

It recognizes two kinds of hand-written admonitions:

- A `Deprecated:` section in the docstring.
- An admonition whose title matches the extension's `title` option
  (case-insensitive).

For example:

```python
if TYPE_CHECKING:
    Widget: TypeAlias = _Widget
    """A widget that does widget things.

    Deprecated:
        Deprecated since v1.2.0. Use [`mypkg.newmod.Widget`][] instead, as
        explained in the [migration guide](https://example.com/migration).
    """
```

### Known limitations

Griffe reads Python source code without running it. This means the extension
can't evaluate variables, call functions, or work out values that are only
known at runtime. It only documents a deprecation if it can understand the call
just by reading it.

Here are the main limitations:

- **Messages and alias arguments need literal strings.** Enum messages, and
  the alias name, `new_module`, `new_name`, and `since`, must be written as
  string literals in the call. Constants, f-strings, and strings joined with
  `+` aren't evaluated. Adjacent string literals are fine, because Python joins
  them automatically. If an argument isn't a literal, the enum member or the
  alias isn't marked. The `message` argument is never read for module aliases.

- **Alias entries must appear directly in the call.** Each entry must be a
  `DeprecatedAlias(...)` call inside `deprecated_aliases()`. Entries stored in
  variables or unpacked from a collection can't be read. For example, neither
  of these entries will be marked:

  ```python
  deprecated_aliases(__name__, WIDGET)
  deprecated_aliases(__name__, *ALIASES)
  ```

- **Arguments can't be unpacked.** Calls to `deprecated_member()`,
  `DeprecatedMember`, and `DeprecatedAlias` must use explicit arguments, not
  `*args` or `**kwargs`. For example, a member defined as
  `deprecated_member(*ARGS)` isn't marked.

The extension logs every case it skips at debug level. You can see these logs
with `mkdocs build --verbose`.

### Options

| Option                     | Default                                     | Effect                                                                  |
|----------------------------|---------------------------------------------|-------------------------------------------------------------------------|
| `kind`                     | `danger`                                    | The kind of the admonition, which is also its CSS class.                |
| `title`                    | `Deprecated`                                | The title of the admonition. An empty title or `null` means no title.   |
| `label`                    | `deprecated`                                | The label added to deprecated objects. `null` means no label.           |
| `alias_table_functions`    | `frequenz.core.warnings.deprecated_aliases` | The paths of the functions that create a module `__getattr__`.          |
| `alias_classes`            | `frequenz.core.warnings.DeprecatedAlias`    | The paths of the callables that create one alias entry.                 |
| `member_wrapper_functions` | `frequenz.core.enum.deprecated_member`, `frequenz.core.enum.DeprecatedMember` | The paths of the callables that wrap a deprecated enum member's value. |
| `default_message`          | `Deprecated since {since}. Use {new_link} instead.` | The notice for aliases. `{new}` is the replacement's path, and `{new_link}` a link to it in code font, showing only its name if it's in the same module. |
| `show_target`              | `true`                                      | Show an alias' value as its target, instead of the private name.        |

The three path options are lists. If you set one, it replaces the default. To
use your own helper as well as the `frequenz-core` one, list both:

```yaml
extensions:
  - griffe_frequenz_core.deprecations:
      alias_table_functions:
        - frequenz.core.warnings.deprecated_aliases
        - mypkg.compat.moved_to
```

Your own helpers need to take the same arguments as the `frequenz-core` helper
they replace, because the extension reads their calls the same way:

- **Alias tables** work like `deprecated_aliases(module, /, *aliases)`. Every
  positional argument after the module is an alias entry. Keyword arguments are
  ignored.
- **Alias entries** work like `DeprecatedAlias(name, /, *, new_module=None,
  new_name=None, since=None, message=None)`. The name is positional, and
  everything else is passed by keyword. You need to pass `new_module`,
  `new_name` or both, and exactly one of `since` and `message`. Passing `None`
  is the same as not passing the argument.
- **Enum member wrappers** work like `deprecated_member(value, message)`. You
  can pass both arguments positionally or by keyword.

If `frequenz-core` renames or moves a helper, you can update these options with
the new path. You don't need to wait for a new release of this package.

There is one difference from `griffe-warnings-deprecated`, on purpose. If
`title` is empty, `griffe-warnings-deprecated` puts the message in the
admonition title, but this extension doesn't, for two reasons:

- The notice contains a link to the replacement, which doesn't belong in a
  title.
- The extension uses the title to recognize hand-written admonitions.

## Supported Platforms

The following platforms are officially supported (tested):

- **Python:** 3.11
- **Operating System:** Ubuntu Linux 20.04
- **Architectures:** amd64, arm64

## Contributing

If you want to know how to build this project and contribute to it, please
check out the [Contributing Guide](CONTRIBUTING.md).
