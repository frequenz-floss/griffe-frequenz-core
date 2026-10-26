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
- Stores the deprecation message in the object's `deprecated` field.
- Adds an admonition with the message at the top of its docstring.

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

The helper takes a table that maps each old name to the module where the
object lives now. If the object was also renamed, you can write the target as
`"module:name"`.

For example:

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

Suppose this code is in `mypkg.oldmod`. Here's what happens in the generated
documentation:

- **`Widget`** gets the message "`mypkg.oldmod.Widget` is deprecated. Use
  `mypkg.newmod.Widget` instead." The replacement is linked, and its value is
  shown as `mypkg.newmod.Widget` instead of the private `_Widget`.
- **`Doohickey`** points to `mypkg.newmod.Gadget`, because both the module and
  the name changed.

A few other things worth knowing:

- **You don't need a `TYPE_CHECKING` declaration for every alias.** The
  extension marks all aliases in the table as deprecated. If a name isn't
  declared under `TYPE_CHECKING`, it creates a module attribute for it, so the
  alias still appears in the documentation.
- **The message comes from the call, or from `default_message`.** If the call
  passes a `message`, the extension uses it. Otherwise, it uses the
  `default_message` option. In both cases, it replaces `{old}` with the path of
  the alias, formatted as code, and `{new}` with a link to the replacement.
- **Replacement links are optional.** If the replacement isn't in your
  documentation or in a configured inventory, the link is shown as plain code.
  It doesn't make a strict build fail.
- **You can pass the table positionally or as `aliases=`.** Arguments such as
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

Sometimes the generated message isn't enough. For example, you might want to
say since which version the object is deprecated.

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
        `mypkg.oldmod.Widget` is deprecated since v1.2.0. Use
        [`mypkg.newmod.Widget`][] instead.
    """
```

### Known limitations

Griffe reads Python source code without running it. This means the extension
can't evaluate variables, call functions, or work out values that are only
known at runtime. It only documents a deprecation if it can understand the call
just by reading it.

Here are the main limitations:

- **Messages, alias names and targets need literal strings.** They must be
  written as string literals in the call. Constants, f-strings, and strings
  joined with `+` aren't evaluated. If an enum member's message isn't a
  literal, the member isn't marked. If an alias name or target isn't a literal,
  that alias is skipped. If the `message` of an alias table isn't a literal,
  the extension uses `default_message` instead, so the documentation doesn't
  match the runtime warning anymore.

- **The alias table must be a dict written directly in the call.** You can pass
  it as the second positional argument or as `aliases=`. A table stored in a
  variable can't be read, so none of its aliases are marked. For example:

  ```python
  deprecated_aliases(__name__, ALIASES)
  ```

- **Enum wrapper arguments can't be unpacked.** Calls to `deprecated_member()`
  and `DeprecatedMember` must use explicit arguments, positionally or by
  keyword. For example, a member defined as `deprecated_member(*ARGS)` isn't
  marked.

The extension logs every case it skips at debug level. You can see these logs
with `mkdocs build --verbose`.

### Options

| Option                     | Default                                     | Effect                                                                  |
|----------------------------|---------------------------------------------|-------------------------------------------------------------------------|
| `kind`                     | `danger`                                    | The kind of the admonition, which is also its CSS class.                |
| `title`                    | `Deprecated`                                | The title of the admonition. An empty title or `null` means no title.   |
| `label`                    | `deprecated`                                | The label added to deprecated objects. `null` means no label.           |
| `alias_table_functions`    | `frequenz.core.warnings.deprecated_aliases` | The paths of the functions that create a module `__getattr__`.          |
| `member_wrapper_functions` | `frequenz.core.enum.deprecated_member`, `frequenz.core.enum.DeprecatedMember` | The paths of the callables that wrap a deprecated enum member's value. |
| `default_message`          | `{old} is deprecated. Use {new} instead.`   | The alias message, if the call doesn't pass a `message`.                |
| `show_target`              | `true`                                      | Show an alias' value as its target, instead of the private name.        |

The two path options are lists. If you set one, it replaces the default. To use
your own helper as well as the `frequenz-core` one, list both:

```yaml
extensions:
  - griffe_frequenz_core.deprecations:
      alias_table_functions:
        - frequenz.core.warnings.deprecated_aliases
        - mypkg.compat.moved_to
```

Your own helpers need to take the same arguments as the `frequenz-core` helper
they replace, because the extension reads their calls the same way:

- **Alias tables** work like `deprecated_aliases()`. The table is the second
  positional argument or `aliases=`, and the message is `message=`.
- **Enum member wrappers** work like `deprecated_member(value, message)`. You
  can pass both arguments positionally or by keyword.

If `frequenz-core` renames or moves a helper, you can update these options with
the new path. You don't need to wait for a new release of this package.

`default_message` should match the default message of `deprecated_aliases()`,
because that's what the runtime warning says.

There is one difference from `griffe-warnings-deprecated`, on purpose. If
`title` is empty, `griffe-warnings-deprecated` puts the message in the
admonition title, but this extension doesn't, for two reasons:

- The message contains a link to the replacement, which doesn't belong in a
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
