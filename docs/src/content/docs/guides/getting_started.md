---
# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelomas@gmail.com>
#
# SPDX-License-Identifier: CC-BY-4.0

title: Getting started
description: Install SHACL Extractor and generate your first shapes file.
---

## Requirements

- Python 3.10 or later
- [uv](https://github.com/astral-sh/uv) for dependency management

## Installation

Clone the repository:

```bash
git clone https://github.com/skg-if/shacl-extractor.git
```

```bash
cd shacl-extractor
```

Install dependencies:

```bash
uv sync
```

If you want to run the integration tests against the [SKG-IF](https://github.com/skg-if/data-model) ontology, clone with submodules instead:

```bash
git clone --recurse-submodules --remote-submodules https://github.com/skg-if/shacl-extractor.git
```

## Quick start

Point the extractor at an ontology file and choose where to write the output:

```bash
uv run extractor my-ontology.owl shapes.ttl
```

The tool parses every `owl:Class` in the input whose `dc:description` contains property annotations, then writes a SHACL shapes graph in Turtle format.

For a full breakdown of what the annotations look like and how they map to SHACL, see [Annotation syntax](/shacl-extractor/guides/annotation_syntax/).
