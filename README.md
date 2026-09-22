# Griffe Extensions for frequenz-core

[![Build Status](https://github.com/frequenz-floss/griffe-frequenz-core/actions/workflows/ci.yaml/badge.svg)](https://github.com/frequenz-floss/griffe-frequenz-core/actions/workflows/ci.yaml)
[![PyPI Package](https://img.shields.io/pypi/v/griffe-frequenz-core)](https://pypi.org/project/griffe-frequenz-core/)
[![Docs](https://img.shields.io/badge/docs-latest-informational)](https://frequenz-floss.github.io/griffe-frequenz-core/)

## Introduction

A collection of [Griffe](https://mkdocstrings.github.io/griffe/) extensions
that teach [mkdocstrings](https://mkdocstrings.github.io/) about
[`frequenz-core`](https://github.com/frequenz-floss/frequenz-core-python)
helpers.

Some of those helpers express information that Griffe cannot recover from
static analysis alone, so the API documentation generated for code using them
comes out incomplete. Each extension here fills one of those gaps, and new
ones are added as more helpers need the same treatment.

The first gap covered is deprecation. `frequenz-core` marks some APIs as
deprecated through a function call instead of a decorator, which neither the
`@deprecated` decorator support in Griffe nor
[`griffe-warnings-deprecated`](https://mkdocstrings.github.io/griffe-warnings-deprecated/)
can detect.

The extensions match fully qualified names as strings and never import
`frequenz-core`, so this package does not depend on it and can document any
project that uses those helpers.

## Installation

Add `griffe-frequenz-core` to the dependencies your documentation is built
with, next to `mkdocstrings`. Then enable each extension you want by its module
path, in the `extensions` option of the mkdocstrings Python handler.

## Documenting deprecations

The `griffe_frequenz_core.deprecations` extension documents the deprecations
`frequenz-core` expresses through a call. It is meant to run next to
`griffe-warnings-deprecated`, which documents the ones expressed through a
decorator:

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

Its defaults match `griffe-warnings-deprecated`, so with this configuration
both kinds of deprecation are rendered the same way. Every deprecation the
extension recognizes gets the same three things a decorated one gets:

- a `deprecated` label,
- the message stored in the object's `deprecated` field,
- an admonition with the message, inserted at the top of its docstring.

If you have a custom admonition style for deprecations, you can set the `kind`
option to match it.

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

| `frequenz-core` helper                        | Written as                          | Documented object       |
|-----------------------------------------------|-------------------------------------|-------------------------|
| `frequenz.core.warnings.deprecated_aliases()` | the value of a module `__getattr__` | every alias in the table|
| `frequenz.core.enum.deprecated_member()`      | the value of an enum member         | the enum member         |
| `frequenz.core.enum.DeprecatedMember`         | the value of an enum member         | the enum member         |

Calls are matched by the fully qualified path Griffe resolves from the
module's imports, so an import under another name, such as
`from frequenz.core.enum import deprecated_member as dm`, is recognized too.

### Deprecated module aliases

`deprecated_aliases()` keeps a moved symbol importable from its old module
through a module `__getattr__`, with the names declared again under
`TYPE_CHECKING` for type checkers:

```python
from typing import TYPE_CHECKING, TypeAlias

from frequenz.core.warnings import deprecated_aliases

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
        {
            "Widget": "mypkg.newmod",
            "Doohickey": "mypkg.newmod:Gadget",
        },
    )
```

If this is `mypkg.oldmod`, the documentation of `Widget` starts with an
admonition saying "`mypkg.oldmod.Widget` is deprecated. Use
`mypkg.newmod.Widget` instead.", and its value is rendered as
`mypkg.newmod.Widget` instead of the private `_Widget`. A target written as
`"module:name"` renames the symbol as well as moving it, so `Doohickey` points
at `mypkg.newmod.Gadget`.

The details of what gets documented:

- Every name in the table is marked, whether or not it is declared under
  `TYPE_CHECKING`. A name with no declaration gets a new module attribute, so
  it still appears in the documentation.
- The message is the `message` argument of the call when there is one, and the
  `default_message` option otherwise. `{old}` is replaced with the path of the
  alias, formatted as code, and `{new}` with a link to the target. When the
  target is neither in your documentation nor in a configured inventory, the
  link is rendered as plain code instead of failing a strict build.
- The table may be passed positionally or as `aliases=`. The other arguments,
  such as `category` and `stacklevel`, don't change the documentation.
- The call has to be assigned directly to the module's `__getattr__`. A
  `def __getattr__()` that calls `deprecated_aliases()` inside is not
  recognized, and neither is a `__getattr__` built by anything else.

### Deprecated enum members

`deprecated_member()`, or the `DeprecatedMember` class it returns, wraps the
value of an enum member to deprecate it:

```python
from frequenz.core.enum import DeprecatedMember, Enum, deprecated_member


class TaskStatus(Enum):
    OPEN = 1
    PENDING = deprecated_member(1, "PENDING is deprecated, use OPEN instead")
    WAITING = DeprecatedMember(1, "WAITING is deprecated, use OPEN instead")
```

Both members are marked with their message as written, and their value is
rendered as the real value instead of the wrapper call, so the documentation
shows `PENDING = 1`.

### Hand-written admonitions

When the docstring of a deprecated object already has a deprecation
admonition, the extension leaves the docstring alone and only adds the label
and the `deprecated` field. It counts as a deprecation admonition if it is a
`Deprecated:` section, or an admonition whose title matches the `title`
option, ignoring case. Write one when the message is not enough, for example
to say since which version the symbol is deprecated:

```python
if TYPE_CHECKING:
    Widget: TypeAlias = _Widget
    """A widget that does widget things.

    Deprecated:
        `mypkg.oldmod.Widget` is deprecated since v1.2.0. Use
        [`mypkg.newmod.Widget`][] instead.
    """
```

### Known limitations

Griffe reads the source without running it, so a deprecation is only
documented when the call can be understood from the syntax tree alone:

- Messages, alias names and alias targets must be string literals written in
  the call. A message held in a constant, built by an f-string or joined from
  pieces cannot be recovered. An enum member with such a message is left
  unmarked, an alias table entry with such a name or target is skipped, and an
  alias table with such a `message` falls back to the `default_message`
  option, so its documentation no longer matches the runtime warning.
- The arguments of `deprecated_member()` and `DeprecatedMember` must be
  positional. `deprecated_member(1, message="...")` is not recognized, and the
  member is left unmarked.

Each case the extension skips is logged at debug level, which
`mkdocs build --verbose` shows.

### Options

| Option                     | Default                                     | Effect                                                                  |
|----------------------------|---------------------------------------------|-------------------------------------------------------------------------|
| `kind`                     | `danger`                                    | The kind of the admonition, which is also its CSS class.                |
| `title`                    | `Deprecated`                                | The title of the admonition. An empty title or `null` renders none.     |
| `label`                    | `deprecated`                                | The label added to deprecated objects. `null` adds none.                |
| `alias_table_functions`    | `frequenz.core.warnings.deprecated_aliases` | The paths of the functions that build a module `__getattr__`.           |
| `member_wrapper_functions` | `frequenz.core.enum.deprecated_member`, `frequenz.core.enum.DeprecatedMember` | The paths of the callables that wrap a deprecated enum member's value. |
| `default_message`          | `{old} is deprecated. Use {new} instead.`   | The alias message used when the call passes no `message`.               |
| `show_target`              | `true`                                      | Render an alias' value as its target, not the private name.             |

The two path options are lists, and setting one replaces its default. To match
a helper of your own as well as the `frequenz-core` one, list both:

```yaml
extensions:
  - griffe_frequenz_core.deprecations:
      alias_table_functions:
        - frequenz.core.warnings.deprecated_aliases
        - mypkg.compat.moved_to
```

They are options so that, if `frequenz-core` renames or moves a helper, you can
point them at the new path without waiting for a release of this package. For
the same reason, `default_message` has to follow the default of
`deprecated_aliases()`, since that is what the runtime warning says.

There is one deliberate difference from `griffe-warnings-deprecated`: given an
empty `title`, it puts the message in the admonition title, and this
extension does not. The message contains a link to the target, which does not
belong in a title, and the title is also what tells a hand-written admonition
apart.

## Supported Platforms

The following platforms are officially supported (tested):

- **Python:** 3.11
- **Operating System:** Ubuntu Linux 20.04
- **Architectures:** amd64, arm64

## Contributing

If you want to know how to build this project and contribute to it, please
check out the [Contributing Guide](CONTRIBUTING.md).
