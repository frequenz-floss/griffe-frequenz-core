# Griffe Extensions for frequenz-core Release Notes

## Summary

This release follows the final `frequenz.core.warnings.deprecated_aliases()` API released in `frequenz-core` v1.5.0, where every alias is a `DeprecatedAlias` entry saying where the symbol is now, with `new_module`, `new_name` or both, and either the version it is deprecated since or its own message, so each alias is documented saying since which version it is deprecated.

## Upgrading

- The `default_message` option is now the message of an alias entry that gives `since`, and its default changed to `{old} is deprecated since {since}. Use {new} instead.` to match `frequenz-core`. `{since}` is replaced with the entry's `since`. If you set it, add `{since}` to it.

## New Features

- New `alias_classes` option, defaulting to `frequenz.core.warnings.DeprecatedAlias`, listing the callables that build one alias entry, for projects using a helper of their own.

## Bug Fixes

- `griffe_frequenz_core.deprecations` now reads the call shape `frequenz-core` actually released:

  ```python
  __getattr__ = deprecated_aliases(
      __name__,
      DeprecatedAlias("Old", new_module="pkg.new", since="v1.2.0"),
  )
  ```

  v1.0.0 read an earlier dict form, `deprecated_aliases(__name__, {"Old": "pkg.new"}, message="...")`, which never made it into a `frequenz-core` release and is no longer read. Entries are read one by one, so an entry that cannot be read statically (a constant, unpacked arguments, a non-literal argument, neither `new_module` nor `new_name`, both or neither of `since` and `message`, or a message that is not a template of `{old}` and `{new}` only) is skipped with a debug log without affecting the others.
