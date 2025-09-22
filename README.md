# SKG-IF SHACL Extractor

[![Tests](https://github.com/skg-if/shacl-extractor/actions/workflows/tests.yml/badge.svg)](https://github.com/skg-if/shacl-extractor/actions/workflows/tests.yml)
![Coverage](https://byob.yarr.is/arcangelo7/badges/skg-if-shacl-extractor_coverage)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: ISC](https://img.shields.io/badge/License-ISC-blue.svg)](https://opensource.org/licenses/ISC)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)

A Python tool to automatically generate SHACL shapes from OWL ontologies that follow the SKG-IF documentation pattern. The SKG-IF data model is documented at https://skg-if.github.io/data-model/.

## Description

This tool extracts SHACL (Shapes Constraint Language) shapes from OWL ontologies that use a specific documentation pattern for describing class properties. It can work with both the SKG-IF ontology versions and custom ontologies that follow the same documentation pattern.

The tool parses property descriptions in the format:

- propertyName -[cardinality]-> targetType

For example:

- dcterms:title -[1]-> rdfs:Literal
- frapo:hasGrantNumber -[0..1]-> xsd:string
- frapo:hasFundingAgency -[0..N]-> frapo:FundingAgency

The cardinality can be specified as:

- A single number (e.g., [1]) for exact cardinality
- A range with minimum and maximum (e.g., [0..1])
- Using N for unlimited maximum cardinality (e.g., [1..N])

## Requirements

- Python 3.9+
- Poetry for dependency management

## Installation

1. Clone the repository with its submodules (use `--remote-submodules` to get the latest versions):

```bash
git clone --recurse-submodules --remote-submodules https://github.com/skg-if/shacl-extractor.git
```

If you already cloned the repository, you can update submodules to their latest versions with:

```bash
git submodule update --init --remote
```

2. Install dependencies using [Poetry](https://python-poetry.org/):

```bash
poetry install
```

## Usage

The tool can be used in three ways:

### 1. Generate SHACL shapes from current SKG-IF ontology

```bash
poetry run extractor shapes.ttl
```

### 2. Generate SHACL shapes from a specific SKG-IF ontology version

```bash
poetry run extractor --version 1.0.0 shapes.ttl
```

### 3. Generate SHACL shapes from a custom ontology file

```bash
poetry run extractor --input path/to/ontology.ttl shapes.ttl
```

Arguments:

- `--version`: (Optional) Specific version of the SKG-IF ontology to use (e.g., "1.0.0", "current")
- `--input`: (Optional) Path to a custom input OWL ontology file in Turtle (.ttl) format
- `output_file`: Path where the generated SHACL shapes will be saved (in Turtle format)

Note: If neither `--version` nor `--input` is specified, the tool will use the current version of the SKG-IF ontology.

## Testing

Run the unit tests:

```bash
python -m unittest
```

## License

ISC License

## Author

Arcangelo Massari (arcangelo.massari@unibo.it)
