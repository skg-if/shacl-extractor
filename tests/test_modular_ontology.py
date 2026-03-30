# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelomas@gmail.com>
#
# SPDX-License-Identifier: ISC

import unittest.mock
from pathlib import Path

from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDF, OWL

from src.main import (
    SHAPES_BASE,
    create_shacl_shapes,
    load_ontology_by_module,
)
from tests.conftest import TempDirTestCase


class TestModularOntology(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.modular_dir = Path(self.temp_dir) / "modular"
        agent_dir = self.modular_dir / "agent"
        agent_dir.mkdir(parents=True)

        self.test_data = '''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix datacite: <http://purl.org/spar/datacite/> .
@prefix literal: <http://www.essepuntato.it/2010/06/literalreification/> .

foaf:Agent a owl:Class ;
    dc:description """The properties that can be used with this class are:

* datacite:hasIdentifier -[0..N]-> datacite:Identifier
* foaf:name -[0..1]-> rdfs:Literal""" .

datacite:Identifier a owl:Class ;
    dc:description """The properties that can be used with this class are:

* datacite:usesIdentifierScheme -[1]-> datacite:IdentifierScheme
* literal:hasLiteralValue -[1]-> rdfs:Literal""" .

datacite:IdentifierScheme a owl:Class .
'''
        agent_ttl = agent_dir / "skg-o.ttl"
        with open(agent_ttl, 'w', encoding='utf-8') as f:
            f.write(self.test_data)

        rp_dir = self.modular_dir / "research-product"
        rp_dir.mkdir(parents=True)
        with open(rp_dir / "skg-o.ttl", 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix fabio: <http://purl.org/spar/fabio/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .

fabio:Work a owl:Class ;
    dc:description """The properties that can be used with this class are:

* fabio:hasAuthor -[1..N]-> foaf:Agent""" .
''')

        self.root_classes = {"agent": "http://xmlns.com/foaf/0.1/Agent"}

    def test_basic_shape_creation(self):
        shacl_graph = create_shacl_shapes(self.modular_dir, root_classes=self.root_classes)

        SH = Namespace("http://www.w3.org/ns/shacl#")
        FOAF = Namespace("http://xmlns.com/foaf/0.1/")
        shape_uri = URIRef(SHAPES_BASE + "agent/AgentShape")

        self.assertIn((shape_uri, RDF.type, SH.NodeShape), shacl_graph)
        self.assertIn((shape_uri, SH.targetClass, FOAF.Agent), shacl_graph)

    def test_property_constraints(self):
        shacl_graph = create_shacl_shapes(self.modular_dir, root_classes=self.root_classes)

        SH = Namespace("http://www.w3.org/ns/shacl#")
        FOAF = Namespace("http://xmlns.com/foaf/0.1/")
        DATACITE = Namespace("http://purl.org/spar/datacite/")
        XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

        agent_shape = URIRef(SHAPES_BASE + "agent/AgentShape")
        agent_props = list(shacl_graph.objects(agent_shape, SH.property, unique=True))
        self.assertEqual(len(agent_props), 2)

        identifier_shape = URIRef(SHAPES_BASE + "agent/IdentifierShape")
        self.assertIn((identifier_shape, RDF.type, SH.NodeShape), shacl_graph)
        self.assertIsNone(shacl_graph.value(identifier_shape, SH.targetClass))

        for prop_shape in agent_props:
            path = shacl_graph.value(prop_shape, SH.path)
            if path == DATACITE.hasIdentifier:
                self.assertIn((prop_shape, SH.node, identifier_shape), shacl_graph)
            elif path == FOAF.name:
                self.assertIn((prop_shape, SH.nodeKind, SH.Literal), shacl_graph)
                self.assertIn((prop_shape, SH.maxCount, Literal(1, datatype=XSD.integer)), shacl_graph)

        identifier_props = list(shacl_graph.objects(identifier_shape, SH.property, unique=True))
        self.assertEqual(len(identifier_props), 2)

        LITERAL = Namespace("http://www.essepuntato.it/2010/06/literalreification/")
        for prop_shape in identifier_props:
            path = shacl_graph.value(prop_shape, SH.path)
            if path == DATACITE.usesIdentifierScheme:
                self.assertIn((prop_shape, SH.nodeKind, SH.BlankNodeOrIRI), shacl_graph)
                self.assertIn((prop_shape, SH.minCount, Literal(1, datatype=XSD.integer)), shacl_graph)
                self.assertIn((prop_shape, SH.maxCount, Literal(1, datatype=XSD.integer)), shacl_graph)
            elif path == LITERAL.hasLiteralValue:
                self.assertIn((prop_shape, SH.nodeKind, SH.Literal), shacl_graph)
                self.assertIn((prop_shape, SH.minCount, Literal(1, datatype=XSD.integer)), shacl_graph)
                self.assertIn((prop_shape, SH.maxCount, Literal(1, datatype=XSD.integer)), shacl_graph)

        scheme_shape = URIRef(SHAPES_BASE + "agent/IdentifierSchemeShape")
        self.assertNotIn((scheme_shape, RDF.type, SH.NodeShape), shacl_graph)

    def test_no_description(self):
        no_desc_dir = Path(self.temp_dir) / "no_desc_modular"
        agent_dir = no_desc_dir / "agent"
        agent_dir.mkdir(parents=True)

        with open(agent_dir / "skg-o.ttl", 'w', encoding='utf-8') as f:
            f.write("""
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .

foaf:Agent a owl:Class .
""")

        shacl_graph = create_shacl_shapes(no_desc_dir)

        self.assertEqual(len(list(shacl_graph.subjects(RDF.type, URIRef("http://www.w3.org/ns/shacl#NodeShape")))), 0)

    def test_main_function(self):
        output_file = Path(self.temp_dir) / "test_main_output.ttl"

        test_args = ['prog_name', str(self.modular_dir), str(output_file)]
        with unittest.mock.patch('sys.argv', test_args):
            from src.main import main
            main()

        self.assertTrue(output_file.exists())
        from rdflib import Graph
        g = Graph()
        g.parse(output_file, format='turtle')

        SH = Namespace("http://www.w3.org/ns/shacl#")
        self.assertTrue(any(s for s in g.subjects(RDF.type, SH.NodeShape)))

    def test_load_ontology_by_module(self):
        base_dir = Path(self.temp_dir) / "ontology" / "test_version"
        agent_dir = base_dir / "agent"
        agent_dir.mkdir(parents=True)

        with open(agent_dir / "skg-o.ttl", 'w', encoding='utf-8') as f:
            f.write("""
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .

foaf:Agent a owl:Class .
""")

        venue_dir = base_dir / "venue"
        venue_dir.mkdir()
        with open(venue_dir / "skg-o.ttl", 'w', encoding='utf-8') as f:
            f.write("""
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix ex: <http://example.org/> .

ex:Venue a owl:Class .
""")

        resources_dir = base_dir / "resources"
        resources_dir.mkdir()

        modules = load_ontology_by_module(str(base_dir))

        FOAF = Namespace("http://xmlns.com/foaf/0.1/")
        EX = Namespace("http://example.org/")

        self.assertIn("agent", modules)
        self.assertIn("venue", modules)
        self.assertNotIn("resources", modules)
        self.assertIn((FOAF.Agent, RDF.type, OWL.Class), modules["agent"])
        self.assertIn((EX.Venue, RDF.type, OWL.Class), modules["venue"])

    def test_modular_shapes_include_all_modules(self):
        multi_dir = Path(self.temp_dir) / "multi_modular"
        mod_a = multi_dir / "mod-a"
        mod_b = multi_dir / "mod-b"
        mod_a.mkdir(parents=True)
        mod_b.mkdir(parents=True)

        with open(mod_a / "onto.ttl", 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix ex: <http://example.org/a/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:Alpha a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:name -[1]-> rdfs:Literal""" .
''')

        with open(mod_b / "onto.ttl", 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix ex: <http://example.org/b/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:Beta a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:value -[1]-> rdfs:Literal""" .
''')

        shacl_graph = create_shacl_shapes(multi_dir, shapes_base="http://test.org/shapes/")

        SH = Namespace("http://www.w3.org/ns/shacl#")
        alpha_shape = URIRef("http://test.org/shapes/mod-a/AlphaShape")
        beta_shape = URIRef("http://test.org/shapes/mod-b/BetaShape")

        self.assertIn((alpha_shape, RDF.type, SH.NodeShape), shacl_graph)
        self.assertIn((beta_shape, RDF.type, SH.NodeShape), shacl_graph)

    def test_empty_property_description(self):
        test_dir = Path(self.temp_dir) / "empty_prop_test"
        agent_dir = test_dir / "agent"
        agent_dir.mkdir(parents=True)

        with open(agent_dir / "skg-o.ttl", 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

foaf:Agent a owl:Class ;
    dc:description """The properties that can be used are:
* foaf:name -[1]-> xsd:string

*
*
* foaf:mbox -[1]-> xsd:string
""" .
''')

        shacl_graph = create_shacl_shapes(test_dir)

        SH = Namespace("http://www.w3.org/ns/shacl#")
        shape_uri = URIRef(SHAPES_BASE + "agent/AgentShape")
        property_shapes = list(shacl_graph.objects(shape_uri, SH.property))

        self.assertEqual(len(property_shapes), 2)

        FOAF = Namespace("http://xmlns.com/foaf/0.1/")
        properties_found = set()
        for prop_shape in property_shapes:
            path = shacl_graph.value(prop_shape, SH.path)
            if path in [FOAF.name, FOAF.mbox]:
                properties_found.add(path)

        self.assertEqual(len(properties_found), 2)

    def test_class_with_non_property_description(self):
        test_dir = Path(self.temp_dir) / "non_prop_desc_test"
        agent_dir = test_dir / "agent"
        agent_dir.mkdir(parents=True)

        with open(agent_dir / "skg-o.ttl", 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .

foaf:Agent a owl:Class ;
    dc:description "This is just a general description without property info." .
''')

        shacl_graph = create_shacl_shapes(test_dir)

        SH = Namespace("http://www.w3.org/ns/shacl#")
        shapes = list(shacl_graph.subjects(RDF.type, SH.NodeShape))
        self.assertEqual(len(shapes), 0)

    def test_invalid_property_format(self):
        test_dir = Path(self.temp_dir) / "invalid_format_test"
        agent_dir = test_dir / "agent"
        agent_dir.mkdir(parents=True)

        with open(agent_dir / "skg-o.ttl", 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .

foaf:Agent a owl:Class ;
    dc:description """The properties that can be used with this class are:

* foaf:name INVALID FORMAT HERE""" .
''')

        with self.assertRaises(ValueError) as context:
            create_shacl_shapes(test_dir)

        self.assertIn("Invalid property format", str(context.exception))

    def test_unknown_property_prefix(self):
        test_dir = Path(self.temp_dir) / "unknown_prop_prefix_test"
        agent_dir = test_dir / "agent"
        agent_dir.mkdir(parents=True)

        with open(agent_dir / "skg-o.ttl", 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

foaf:Agent a owl:Class ;
    dc:description """The properties that can be used with this class are:

* unknownprefix:property -[1]-> rdfs:Literal""" .
''')

        with self.assertRaises(ValueError) as context:
            create_shacl_shapes(test_dir)

        self.assertIn("Unknown prefix 'unknownprefix'", str(context.exception))

    def test_unknown_target_prefix(self):
        test_dir = Path(self.temp_dir) / "unknown_target_prefix_test"
        agent_dir = test_dir / "agent"
        agent_dir.mkdir(parents=True)

        with open(agent_dir / "skg-o.ttl", 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .

foaf:Agent a owl:Class ;
    dc:description """The properties that can be used with this class are:

* foaf:name -[1]-> unknowntarget:Type""" .
''')

        with self.assertRaises(ValueError) as context:
            create_shacl_shapes(test_dir)

        self.assertIn("Unknown prefix 'unknowntarget'", str(context.exception))
