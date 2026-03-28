---
# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelomas@gmail.com>
#
# SPDX-License-Identifier: CC-BY-4.0

title: CLI reference
description: Command-line interface for the SHACL Extractor.
---

## Synopsis

```bash
uv run extractor <input> <output> [--shapes-base URL] [--root-classes FILE]
```

## Arguments

### `input`

The ontology source. Accepts:

- A local file path (`.ttl`, `.rdf`, `.owl`, `.n3`, `.nt`, `.jsonld`)
- A local directory containing subdirectories with ontology files
- An HTTP or HTTPS URL pointing to a remote ontology

### `output`

Where to write the generated SHACL shapes. The output is always Turtle format.

### `--shapes-base`

Override the base URL for the shapes namespace. Without this flag, the namespace is derived automatically:

- **Modular directory input**: defaults to `https://w3id.org/skg-if/shapes/`
- **Single file or URL**: derived from the ontology IRI (e.g., `https://example.org/myonto/shapes/`)
- **If no ontology IRI is found**: falls back to `http://example.org/shapes/`

You typically need this flag for extension ontologies, where the auto-derived namespace doesn't match the intended one.

### `--root-classes`

Path to a JSON file that explicitly sets which classes get `sh:targetClass`. The file maps module names to class URIs:

```json
{
    "agent": "http://xmlns.com/foaf/0.1/Agent",
    "grant": "http://purl.org/cerif/frapo/Grant"
}
```

Without this flag, root classes are detected automatically: any described class that no other described class points to as a target is treated as root. This heuristic fails when classes reference each other across modules (e.g., `Agent` referenced by `Grant`), in which case you need this flag.
