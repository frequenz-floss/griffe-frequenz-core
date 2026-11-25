# Griffe Extensions for frequenz-core Release Notes

## Summary

The extension now documents tables made with `deprecated_symbols()`, the new name of `deprecated_aliases()` in `frequenz-core` 1.7.0.

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

## New Features

- The extension reads `frequenz.core.warnings.deprecated_symbols()` tables. This is the new name of `deprecated_aliases()` in `frequenz-core` 1.7.0. The old name is still read, so you don't need to change your code to upgrade.

  If you set `alias_table_functions`, add `frequenz.core.warnings.deprecated_symbols` to your list.

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
