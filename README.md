<!--
SPDX-FileCopyrightText: 2025 Silvio Peroni <essepuntato@gmail.com>
SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelomas@gmail.com>

SPDX-License-Identifier: CC-BY-4.0
-->

# SHACL Extractor

[![Tests](https://github.com/skg-if/shacl-extractor/actions/workflows/tests.yml/badge.svg)](https://github.com/skg-if/shacl-extractor/actions/workflows/tests.yml)
[![Coverage](https://skg-if.github.io/shacl-extractor/coverage/coverage-badge.svg)](https://skg-if.github.io/shacl-extractor/coverage/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: ISC](https://img.shields.io/badge/License-ISC-blue.svg)](https://opensource.org/licenses/ISC)
[![REUSE](https://github.com/skg-if/shacl-extractor/actions/workflows/reuse.yml/badge.svg)](https://github.com/skg-if/shacl-extractor/actions/workflows/reuse.yml)

Generates SHACL shapes from OWL ontologies that document class properties in `dc:description` annotations.

## Quick start

```bash
git clone https://github.com/skg-if/shacl-extractor.git
```

```bash
cd shacl-extractor
```

```bash
uv sync
```

```bash
uv run extractor my-ontology.owl shapes.ttl
```

## Documentation

Full documentation at [skg-if.github.io/shacl-extractor](https://skg-if.github.io/shacl-extractor/).
