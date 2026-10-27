# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Griffe extensions to help mkdocstrings understand frequenz-core helpers.

Some `frequenz-core` helpers use patterns that [Griffe] can't fully understand
by just reading the source code. This means that some information might be
missing from the generated API documentation. Each extension in this package
fills in one of these gaps, and we add new ones when more helpers need it.

The extensions recognize helpers by their fully qualified names, without
importing `frequenz-core`. So this package doesn't depend on `frequenz-core`,
and you can use it to document any project that uses these helpers.

Each extension lives in its own submodule, and you enable it using the
submodule's path, for example `griffe_frequenz_core.deprecations`.

Nothing is re-exported here on purpose. When you enable a module path, Griffe
creates *every* extension class it finds in that module, all with the same
options. So if this package re-exported the extensions, enabling it would pass
the same options to unrelated extensions as soon as we add a second one.

Available extensions:

- [`deprecations`][griffe_frequenz_core.deprecations]: Deprecations made with
  a function call instead of a decorator.

[Griffe]: https://mkdocstrings.github.io/griffe/
"""
