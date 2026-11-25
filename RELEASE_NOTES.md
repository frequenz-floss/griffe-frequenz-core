# Griffe Extensions for frequenz-core Release Notes

## Summary

The extension now documents what `frequenz-core` 1.7.0 adds for module attributes: tables made with `deprecated_symbols()`, the new name of `deprecated_aliases()`, and their `DeprecatedSymbol` entries.

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

## New Features

- The extension reads `frequenz.core.warnings.deprecated_symbols()` tables. This is the new name of `deprecated_aliases()` in `frequenz-core` 1.7.0. The old name is still read, so you don't need to change your code to upgrade.

  If you set `alias_table_functions`, add `frequenz.core.warnings.deprecated_symbols` to your list.

- The extension documents `frequenz.core.warnings.DeprecatedSymbol` entries. They deprecate a constant, type variable or type alias that isn't moving.

  ```python
  __getattr__ = deprecated_symbols(
      __name__,
      DeprecatedSymbol(
          "TIMEOUT_SECONDS",
          value=_TIMEOUT_SECONDS,
          replacement="mypkg.TIMEOUT",
          since="v1.5.0",
      ),
  )
  ```

  The symbol gets the notice "Deprecated since v1.5.0. Use `TIMEOUT` instead.", with a link to the replacement. Its value is shown as the one in `_TIMEOUT_SECONDS`, not as the private name.

  A symbol without `replacement` needs a hand-written `Deprecated:` notice. Without one, the extension shows the runtime `message` and logs a warning.

  Alias and symbol entries can be in the same table. The new `symbol_classes` option lists the classes read as `DeprecatedSymbol`.

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
