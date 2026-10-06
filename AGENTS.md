# AGENTS.md

Griffe extensions that document what `frequenz-core` helpers do with function calls, like deprecations. Run `nox` and `mkdocs build --strict` before committing.

## Rules

- Only read the documented code statically. Never import or run it, and only use string literals written in the call.
- Match how `frequenz-core` works at runtime (argument matching, defaults, path resolution) exactly, and test it in `tests/compat` against the pinned version. Don't validate argument values beyond that: the extension documents code, it doesn't lint it.
- Follow the deprecations guide (frequenz-floss/docs `python/deprecations.md`). The runtime warning is for a terminal. The notice is for the docs: it says since which version the object is deprecated and links what to use instead.
- Document as much as can be read, the same way for every helper. Mark every object that can be identified, and use generic text for what can't be read.
- Never hide problems. If a notice is missing something the guide asks for, or the docs can't show something in full, log a warning, so `--strict` fails. Use debug logs only to explain why.
- Only show a runtime warning as the notice if there is nothing better, generated or hand-written. Show it as written, render it as Markdown, and log a warning.
- A hand-written notice always takes priority. On objects the extension marks, move it to the top of the docstring.
- Text the extension writes is only for the docs. Don't repeat the name of the documented object, and link objects in code font, like ``[`pkg.Name`][]``, or ``[`Name`][pkg.Name]`` in the same module.
- Never make links optional: a link that can't be resolved must be reported.
- Update the README, docstrings, tests and release notes with every behavior change.
- Write docs, docstrings, log messages and commit messages in simple English: short sentences, active voice, and the main point first.
