---
title: SKG-IF JSON-LD Context
layout: default
nav_order: 4
---

# SKG-IF JSON-LD Context

The [Github repository](https://github.com/skg-if/context) contains everything that is relevant to the JSON-LD context.
It includes samples, conversion scripts and a version tracking folder.

The current (i.e., last) version of the JSON-LD context is available at [https://w3id.org/skg-if/context/skg-if.json](https://w3id.org/skg-if/context/skg-if.json). The following toy examples for each entity defined by the [SKG-IF interoperability framework](/interoperability-framework/) are also available online:

* [Agent]
* [Data source]
* [Grant]
* [Research product]
* [Topic]
* [Venue](docs/samples/example-venue.json)

One can access the JSON-LD contexts of all (current and previous) versions by using a version number in the `w3id.org` URL, before the name of the JSON file, following this pattern:

```
https://w3id.org/skg-if/context/<X.Y.Z>/skg-if.json
```

For instance:
* `https://w3id.org/skg-if/context/1.0.0/skg-if.json` allows to access to version 1.0.0 of the JSON-LD context;
* `https://w3id.org/skg-if/context/0.2.0/skg-if.json` allows to access to version 0.2.0 of the JSON-LD context;
* and so on.

----
[Agent]: {% link context/ver/current/samples/example-agent.json %}
[Data source]: {% link context/ver/current/samples/example-data-source.json %}
[Grant]: {% link context/ver/current/samples/example-grant.json %}
[Research product]: {% link context/ver/current/samples/example-research-product.json %}
[Topic]: {% link context/ver/current/samples/example-topic.json %}
[Venue]: {% link context/ver/current/samples/example-venue.json %}