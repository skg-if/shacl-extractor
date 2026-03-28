---
# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelomas@gmail.com>
#
# SPDX-License-Identifier: CC-BY-4.0

title: Annotation syntax
description: How the extractor reads dc:description annotations and translates them to SHACL.
---

The extractor looks for `owl:Class` definitions that carry a `dc:description` annotation containing the phrase "The properties that can be used". Everything after that line is parsed as a list of property declarations.

## Property format

Each property is a bullet point (`*` or `-`) followed by this pattern:

```
prefix:propertyName -[cardinality]-> prefix:TargetType
```

A concrete example in a Turtle ontology:

```turtle
foaf:Agent a owl:Class ;
    dc:description """The properties that can be used with this class are:

* datacite:hasIdentifier -[0..N]-> datacite:Identifier
* foaf:name -[0..1]-> rdfs:Literal
* pro:holdsRoleInTime -[0..N]-> pro:RoleInTime""" .
```

The extractor turns each line into an `sh:property` block on the corresponding `NodeShape`.

## Cardinality

Three forms are recognized:

| Notation | Meaning | SHACL output |
|---|---|---|
| `[2]` | Exactly 2 | `sh:minCount 2 ; sh:maxCount 2` |
| `[0..1]` | Zero or one | `sh:maxCount 1` |
| `[1..N]` | At least one, no upper bound | `sh:minCount 1` |

`N` and `*` both mean unbounded. When the minimum is `0` or unbounded, no `sh:minCount` is emitted. When the maximum is `N` or `*`, no `sh:maxCount` is emitted.

## Target types

What the extractor generates depends on the target type:

**Literals.** `rdfs:Literal` and `rdfs:langString` produce `sh:nodeKind sh:Literal`. XSD types like `xsd:string` or `xsd:dateTime` produce `sh:datatype`.

**Classes with a shape.** When the target class also has its own `dc:description` block, the extractor generates `sh:node TargetShape`. This links the property constraint to the shape of the target class, so values are validated against its properties too.

**Classes without a shape.** If the target class has no property annotations (and therefore no generated shape), the extractor falls back to `sh:nodeKind sh:BlankNodeOrIRI`.

## Union ranges

When the same property path appears multiple times with different target classes, the extractor treats it as a union range and generates a single `sh:property` with `sh:or`.

Consider this annotation, where `srv:isDeploymentOf` can point to three different classes:

```
* srv:isDeploymentOf -[0..N]-> fabio:Software
* srv:isDeploymentOf -[0..N]-> schema:SoftwareSourceCode
```

Suppose `schema:SoftwareSourceCode` has its own `dc:description` block (so the extractor generates a `SoftwareSourceCodeShape` for it), while `fabio:Software` do not. The result is:

```turtle
sh:property [
    sh:path srv:isDeploymentOf ;
    sh:or (
        [ sh:nodeKind sh:BlankNodeOrIRI ]
        [ sh:node srv_sh:SoftwareSourceCodeShape ]
    ) ;
] ;
```

## Namespace resolution

Prefixes in the annotations need to be resolved to full URIs. The extractor tries three strategies in order:

1. **Registered prefixes** -- standard `@prefix` declarations parsed by rdflib.
2. **URI namespace map** -- when a target name appears without a prefix (e.g., just `E55_Type`), the extractor looks it up against all URIs already present in the graph. If any URI ends with `E55_Type` after a `#` or `/`, the namespace part of that URI is used.
3. **Literal prefix map** -- parses `@prefix` declarations found inside string literals (i.e., inside `dc:description` text itself). Some ontologies declare prefixes only in annotation strings, not at the top level. CHAD-AP is one such case: `crm:`, `lrmoo:`, and `crmdig:` appear [only inside a `dc:description` literal](https://github.com/dharc-org/chad-ap/blob/main/docs/current/chad-ap.ttl#L106), never as top-level `@prefix` declarations.

## Root classes

A root class gets `sh:targetClass` in its shape, meaning SHACL validators will check all instances of that class against the shape. Non-root classes only get `sh:NodeShape` without a target -- they are validated indirectly when referenced via `sh:node` from another shape.

By default, the extractor detects root classes automatically: a class is root if no other described class points to it as a target. This works well for ontologies with a clear hierarchy, where top-level classes are never referenced as the range of another class's property.

It breaks down when classes reference each other across modules. In [SKG-IF core](https://github.com/skg-if/data-model), for instance, `Agent` is referenced by `Grant` (via `pro:isHeldBy`), `Work` is referenced by `DataService`, and so on -- almost every top-level entity appears as someone else's target. The automatic algorithm would miss them all, since it only picks classes with zero incoming edges.

For these cases, use `--root-classes` to specify the root classes explicitly via a JSON file that maps module names to class URIs. The repository ships a [preset for SKG-IF core](https://github.com/skg-if/shacl-extractor/blob/main/presets/skg-if-core.json):

```bash
uv run extractor data-model/ontology/current/ shapes.ttl --root-classes presets/skg-if-core.json
```
