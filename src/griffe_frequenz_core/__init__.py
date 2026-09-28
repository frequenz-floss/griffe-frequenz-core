# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""A collection of Griffe extensions to teach mkdocstrings about frequenz-core helpers.

Some `frequenz-core` helpers express information that [Griffe] cannot recover
from static analysis alone, so the API documentation generated for code using
them comes out incomplete. Each extension in this package fills one of those
gaps, and new ones are added as more helpers need the same treatment.

The extensions match fully qualified names as strings and never import
`frequenz-core`, so this package doesn't depend on it and can document any
project that uses those helpers.

Each extension lives in its own submodule and is enabled by that submodule's
path, for example `griffe_frequenz_core.deprecations`. Nothing is re-exported
here on purpose: Griffe instantiates *every* extension class it finds at a bare
module path with the same options, so a package-level entry would start
configuring unrelated extensions the day a second one lands.

Available extensions:

- [`deprecations`][griffe_frequenz_core.deprecations]: deprecations expressed
  as a function call rather than a decorator.

[Griffe]: https://mkdocstrings.github.io/griffe/
"""
