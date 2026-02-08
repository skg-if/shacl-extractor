# SHACL Extractor

[![Tests](https://github.com/skg-if/shacl-extractor/actions/workflows/tests.yml/badge.svg)](https://github.com/skg-if/shacl-extractor/actions/workflows/tests.yml)
![Coverage](https://byob.yarr.is/arcangelo7/badges/skg-if-shacl-extractor_coverage)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: ISC](https://img.shields.io/badge/License-ISC-blue.svg)](https://opensource.org/licenses/ISC)
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

- Python 3.9+
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

- `input`: Input ontology source. Can be a file path, a directory (for modular ontologies), or a URL
- `output`: Path where the generated SHACL shapes will be saved (in Turtle format)
- `--shapes-base`: (Optional) Custom base URL for the shapes namespace

### Examples

Generate shapes from a single ontology file:

```bash
uv run extractor my-ontology.ttl shapes.ttl
```

Generate shapes from a modular ontology directory:

```bash
uv run extractor path/to/ontology/ shapes.ttl
```

Generate shapes from a remote ontology:

```bash
uv run extractor https://example.org/ontology.ttl shapes.ttl
```

Use a custom shapes namespace:

```bash
uv run extractor my-ontology.ttl shapes.ttl --shapes-base https://example.org/shapes/
```
## Testing

Run the tests:

```bash
uv run pytest
```

## License

ISC License

## Author

Arcangelo Massari (arcangelo.massari@unibo.it)
