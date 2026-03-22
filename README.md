<!--
SPDX-FileCopyrightText: 2025 Silvio Peroni <essepuntato@gmail.com>
SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelomas@gmail.com>

SPDX-License-Identifier: ISC
-->

# SHACL Extractor

[![Tests](https://github.com/skg-if/shacl-extractor/actions/workflows/tests.yml/badge.svg)](https://github.com/skg-if/shacl-extractor/actions/workflows/tests.yml)
[![Coverage](https://skg-if.github.io/shacl-extractor/coverage/coverage-badge.svg)](https://skg-if.github.io/shacl-extractor/coverage/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: ISC](https://img.shields.io/badge/License-ISC-blue.svg)](https://opensource.org/licenses/ISC)
[![REUSE](https://github.com/skg-if/shacl-extractor/actions/workflows/reuse.yml/badge.svg)](https://github.com/skg-if/shacl-extractor/actions/workflows/reuse.yml)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

A Python tool to generate SHACL shapes from OWL ontologies that document class properties using `dc:description` annotations.

## Description

This tool extracts SHACL (Shapes Constraint Language) shapes from OWL ontologies that use a specific documentation pattern for describing class properties. It supports single-file ontologies, modular ontology directories, and remote ontologies via URL.

The tool parses property descriptions embedded in `dc:description` annotations using the format:

```
prefix:propertyName -[cardinality]-> prefix:TargetType
```

For example:

- `dcterms:title -[1]-> rdfs:Literal`
- `frapo:hasGrantNumber -[0..1]-> xsd:string`
- `frapo:hasFundingAgency -[0..N]-> frapo:FundingAgency`
- `crm:P4_has_time-span -[1]-> crm:E52_Time-Span`

The cardinality can be specified as:

- A single number (e.g., `[1]`) for exact cardinality
- A range with minimum and maximum (e.g., `[0..1]`)
- Using `N` for unlimited maximum cardinality (e.g., `[1..N]`)

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) for dependency management

## Installation

1. Clone the repository:

```bash
git clone https://github.com/skg-if/shacl-extractor.git
```

Optionally, clone with submodules for running integration tests against the SKG-IF ontology:

```bash
git clone --recurse-submodules --remote-submodules https://github.com/skg-if/shacl-extractor.git
```

2. Install dependencies using [uv](https://github.com/astral-sh/uv):

```bash
uv sync
```

## Usage

```bash
uv run extractor <input> <output> [--shapes-base URL]
```

Arguments:

- `input`: Input ontology source. Can be a file path (`.ttl`, `.rdf`, `.owl`, `.n3`, `.nt`, `.jsonld`), a directory (for modular ontologies), or a URL
- `output`: Path where the generated SHACL shapes will be saved (in Turtle format)
- `--shapes-base`: (Optional) Custom base URL for the shapes namespace

### Examples

Generate shapes from a single ontology file:

```bash
uv run extractor my-ontology.owl shapes.ttl
```

Generate shapes from a modular ontology directory (expects subdirectories, each containing an RDF file — currently tailored to the SKG-IF core structure):

```bash
uv run extractor path/to/ontology/ shapes.ttl
```

Generate shapes from a remote ontology:

```bash
uv run extractor https://example.org/ontology.ttl shapes.ttl
```

Use a custom shapes namespace:

```bash
uv run extractor my-ontology.owl shapes.ttl --shapes-base https://example.org/shapes/
```

### SKG-IF Extension ontologies following the `ext-<name>` convention

SKG-IF extension ontologies (e.g. `ext-srv`, `ext-foo`) are typically stored in a repository whose top-level directory is named `ext-<name>`. When the input is a local file inside such a directory hierarchy, the tool automatically uses `<name>` as the identifier for the generated shapes namespace prefix (e.g. `srv_sh:`). This overrides the default behaviour of deriving the identifier from the ontology IRI, which for extensions typically ends in a generic segment like `ontology/` and would produce an unhelpful prefix such as `ontology_sh:`.

The `--shapes-base` option is also needed for extension ontologies. Without it, the shapes namespace is auto-derived from the ontology IRI (e.g. `https://w3id.org/skg-if/extension/srv/ontology/shapes/`), which is usually not the intended namespace. Supply the correct shapes base explicitly.

The extension repository must be available locally, cloned using its `ext-<name>` directory name.

For example, for the ext-srv extension checked out as `ext-srv/`:

```bash
uv run extractor path/to/ext-srv/data-model/ontology/current/srv.ttl shapes.ttl \
  --shapes-base https://w3id.org/skg-if/shapes/srv/
```

This produces shapes in the `https://w3id.org/skg-if/shapes/srv/` namespace with prefix `srv_sh:`.

## Testing

Run the tests:

```bash
uv run pytest
```

## License

ISC License

## Author

Arcangelo Massari (arcangelo.massari@unibo.it)
