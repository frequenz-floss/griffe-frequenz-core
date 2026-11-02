# Griffe Extensions for frequenz-core Release Notes

## Summary

This release supports the `frequenz.core.warnings.deprecated_aliases()` API from `frequenz-core` v1.5.0 and v1.6.0. Each alias is a `DeprecatedAlias` entry. The entry says where the object is now, using `new_module`, `new_name` or both. You can pass `since` to say when the old name became deprecated, and `message` to change its runtime warning. In v1.6.0, these two arguments are optional and independent.

The extension now also follows the [deprecations guide](https://github.com/frequenz-floss/docs/blob/v0.x.x/python/deprecations.md). The guide separates the runtime warning, which is shown in a terminal, from the notice in the documentation. The notice says since which version the object is deprecated, and links to what to use instead.

The extension generates the notice when the code has enough information. A hand-written `Deprecated:` notice always takes priority. If a notice is missing something the guide asks for, the extension logs a warning.

## Upgrading

- The `default_message` option is now used for the notice of every alias and enum member with `new_name`. Its default is now `Deprecated since {since}. Use {new_link} instead.`:

  - `{old}` and `{new}` are now plain paths.
  - `{new_link}` is a link to the replacement in code font. If the replacement is in the same module or enum, the link only shows its name.
  - The result is rendered as Markdown.

  If you changed `default_message`, add `{since}`, and use `{new_link}` or write the link yourself, like ``[`{new}`][]``.

- The `message` of an alias is now only used for the runtime warning, not for the notice. If an alias has no `since`, its notice is ``Deprecated. Use [`<new>`][] instead.``, and the extension logs a warning. Pass `since` or write a `Deprecated:` section in the docstring of the alias declared under `TYPE_CHECKING`.

- If you deprecate an enum member using only a `message`, you now need to write its `Deprecated:` notice by hand. You can pass `new_name` and `since` instead, if the member has a replacement (see [New Features](#new-features)). Without either change, the extension still shows the runtime warning as the notice, but also logs a warning. If you pass `since`, the notice starts with `Deprecated since <since>.`, followed by the warning.

- The extension now logs a warning when the documentation can't show a deprecation the way the guide asks for, so `mkdocs build --strict` fails. This happens when:

  - A notice doesn't say since which version the object is deprecated, or what to use instead.
  - A runtime warning is shown as the notice.
  - A value is shown as written in the source, because the extension can't read the alias target, or the enum wrapper's arguments are unpacked.
  - A deprecation can't be marked at all.
  - The arguments of a call don't match the ones of the runtime helper.

  To fix these warnings, write the arguments as string literals, or write the `Deprecated:` notice by hand.

- `mkdocs-autorefs` now reports alias targets it can't resolve. To fix this, add the inventory of the target's project.

## New Features

- The extension now reads the `new_name` and `since` arguments added to `deprecated_member()` and `DeprecatedMember` in `frequenz-core` v1.6.0. If you pass both, it generates a notice using `default_message`:

  ```text
  Deprecated since <since>. Use <new_name> instead.
  ```

  The replacement links to the member in the same enum. Without `since`, the notice only says what to use instead, and the extension logs a warning. If you also pass a `message`, it only changes the runtime warning, not the notice. The only exception is when `new_name` isn't a string literal: then the notice shows the message, because it's the only thing that can say what to use instead.

- The new `alias_classes` option lists the callables that create alias entries. It defaults to `frequenz.core.warnings.DeprecatedAlias`. You can use it if your project has its own helper.

- The extension moves hand-written `Deprecated:` notices on aliases and enum members to the top of the docstring, where generated notices go. This way, all notices are in the same place.

## Bug Fixes

- `griffe_frequenz_core.deprecations` now reads the calls the way `frequenz-core` actually released them:

  ```python
  __getattr__ = deprecated_aliases(
      __name__,
      DeprecatedAlias("Old", new_module="pkg.new", since="v1.2.0"),
  )
  ```

  v1.0.0 read an earlier dict form, `deprecated_aliases(__name__, {"Old": "pkg.new"}, message="...")`. That form was never released in `frequenz-core`, so the extension doesn't read it anymore. Each entry is read separately, so if one can't be read, the others are still documented.

- The notice of an alias is now ``Deprecated since <since>. Use [`<new>`][] instead.``. It doesn't repeat the name of the alias, and if the target is in the same module, the link only shows its name.

- If the extension can't read some arguments of a deprecation, it now still documents it, with a generic notice. Before, the object wasn't marked at all. The notice includes the information the extension could read: since which version, and what to use instead. If it can't read either, it only says that the object will be removed in a future release.

  - For an alias, only the name has to be a string literal. Its value is shown as the target if `new_module` and `new_name` can be read.
  - For an enum member like `BREAKER = deprecated_member(7, _member_message("BREAKER"))`, the documentation now shows `BREAKER = 7`, instead of the whole wrapper call.

  A hand-written `Deprecated:` notice is still used instead of the generic one.
