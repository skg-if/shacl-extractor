<!--
SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>

SPDX-License-Identifier: CC-BY-4.0
-->

# SHACL Extractor

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
