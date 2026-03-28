---
# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelomas@gmail.com>
#
# SPDX-License-Identifier: CC-BY-4.0

title: Input modes
description: Single file, modular directory, URL, and extension ontology inputs.
---

The extractor accepts three kinds of input. It figures out which one you mean from the argument you pass.

## Single file

Any file with a recognized RDF extension (`.ttl`, `.rdf`, `.owl`, `.n3`, `.nt`, `.jsonld`):

```bash
uv run extractor my-ontology.owl shapes.ttl
```

The module name -- used in the shapes namespace prefix -- is derived from the ontology IRI found in the file. If the file declares `<https://example.org/myonto> a owl:Ontology`, the module name becomes `myonto` and shapes land in `https://example.org/myonto/shapes/`.

## Modular directory

A directory where each subdirectory holds one module's ontology file. This matches the structure of the [SKG-IF core data model](https://github.com/skg-if/data-model):

```
data-model/ontology/current/
├── agent/
│   └── skg-o.ttl
├── grant/
│   └── skg-o.ttl
├── research-product/
│   └── skg-o.ttl
└── ...
```

```bash
uv run extractor data-model/ontology/current/ shapes.ttl
```

Each subdirectory name becomes a module. Shapes get per-module namespace prefixes like `skg_sh_agent:`, `skg_sh_grant:`, etc.

## URL

A remote ontology fetched over HTTP(S):

```bash
uv run extractor https://example.org/ontology.ttl shapes.ttl
```

Behaves like a single file once downloaded. The module name is derived from the ontology IRI or, failing that, from the URL path.

## Extension ontologies

SKG-IF extensions follow a naming convention: the repository directory is called `ext-<name>` (e.g., `ext-srv`). The module identifier is normally derived from the last segment of the ontology IRI. For extensions, that segment is typically `ontology`, which would produce a generic `ontology_sh:` prefix. When the extractor detects an `ext-<name>` directory in the input path, it uses `<name>` instead -- so `ext-srv` gives `srv_sh:`.