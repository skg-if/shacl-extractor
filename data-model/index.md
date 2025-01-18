---
title: SKG-IF Data Model
layout: default
nav_order: 3
---

# SKG-IF Data Model

The SKG-IF Data Model is the metadata model used for the data compliant with the [SKG-IF Interoperability Framwork](/interoperability-framework/).

The SKG-IF Data Model is used to model all the main SKG-IF main entities, their attributes and the relations to other entities. All these aspects are implementeed using the 'language' of the Semantic Web, in particular by re-employing several existing ontological models that have been developed in the past to address specific modelling scenarios compatible with the aims of SKG-IF. 

The SKG-IF Data Model, summarised in convenient [Graffoo diagrams](https://essepuntato.it/graffoo), allows one to record information about the following SKG-IF entities:

* [Agent](#agent), that represents an individual (e.g., a person, an organisation, or another kind of entity being able to act) who is involved in the creation, publication, dissemination, etc. of a research product.
* [Data source](#data-source), a service or platform where a research product (its metadata and files) is stored, preserved, and made discoverable and accessible.
* [Grant](#grant), that describes funding awarded to an agent by a funding body.
* [Research product](#research-product), that may be of four types - research literature, research data, research software, or other.
* [Topic](#topic), that describes the scientific disciplines, subjects and keywords potentially relevant for a research product.
* [Venue](#venue), an entity that models a publishing “gateway” used by an agent to make their research products available to others.

The SKG-IF Data Model has been also implemented as an OWL ontology, i.e. the [SKG-IF Ontology (SKG-O)](https://w3id.org/skg-if/ontology). It is not yet another bibliographic ontology, but rather it is just a place where existing and complementary ontological entities from several other ontologies, all employed in SKG-IF, are grouped together for the purpose of providing descriptive metadata compliant with the SKG-IF Data Model. The SKG-IF data created following the [Interoperability Framework](/interoperability-framework/) are aligned with the SKG-IF Ontology via the [SKG-IF JSON-LD context](/context/).

## Agent
![Agent diagram]({% link data-model/graphs/skg-if-agent.png %})

## Data source
![Data source diagram]({% link data-model/graphs/skg-if-data-source.png %})

## Grant
![Grant diagram]({% link data-model/graphs/skg-if-grant.png %})

## Research product
![Research product diagram]({% link data-model/graphs/skg-if-research-product.png %})

## Topic
![Topic diagram]({% link data-model/graphs/skg-if-topic.png %})

## Venue
![Venue diagram]({% link data-model/graphs/skg-if-venue.png %})








