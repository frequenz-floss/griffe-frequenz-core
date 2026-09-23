# Griffe Extensions for frequenz-core Release Notes

## Summary

This is the first release. It ships a single extension, `griffe_frequenz_core.deprecations`, which documents the deprecations `frequenz-core` expresses through a function call instead of a decorator.

## New Features

- `griffe_frequenz_core.deprecations`: marks module-level aliases deprecated with `frequenz.core.warnings.deprecated_aliases()`, and enum members wrapped in `frequenz.core.enum.deprecated_member()` or `frequenz.core.enum.DeprecatedMember`, the same way `griffe-warnings-deprecated` marks decorator-based deprecations: a `deprecated` label, the message on the object's `deprecated` field, and an admonition at the top of its docstring. Enable it next to `griffe_warnings_deprecated` in the mkdocstrings Python handler `extensions` option.
