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

## Supported Platforms

The following platforms are officially supported (tested):

- **Python:** 3.11
- **Operating System:** Ubuntu Linux 20.04
- **Architectures:** amd64, arm64

## Contributing

If you want to know how to build this project and contribute to it, please
check out the [Contributing Guide](CONTRIBUTING.md).
