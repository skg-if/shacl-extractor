import json
import shutil
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, OWL
from src.main import (
    SHAPES_BASE,
    _derive_module_name,
    _derive_shapes_base,
    _detect_root_classes,
    _extract_prefixes_from_literals,
    _get_ontology_iri,
    _is_url,
    _load_source,
    create_shacl_shapes,
    load_ontology_by_module,
)


class TestModularOntology(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(dir=".")

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

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_basic_shape_creation(self):
        shacl_graph = create_shacl_shapes(self.modular_dir)

        SH = Namespace("http://www.w3.org/ns/shacl#")
        FOAF = Namespace("http://xmlns.com/foaf/0.1/")
        shape_uri = URIRef(SHAPES_BASE + "agent/AgentShape")

        self.assertIn((shape_uri, RDF.type, SH.NodeShape), shacl_graph)
        self.assertIn((shape_uri, SH.targetClass, FOAF.Agent), shacl_graph)

    def test_property_constraints(self):
        shacl_graph = create_shacl_shapes(self.modular_dir)

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


class TestSKGIFIntegration(unittest.TestCase):
    """Integration tests that require the data-model, examples, and context submodules."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(dir=".")
        self.skgif_path = Path("data-model/ontology/current")
        if not self.skgif_path.exists():
            self.skipTest("SKG-IF submodules not available")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_current_ontology_conversion(self):
        output_file = Path(self.temp_dir) / "current_ontology_shapes.ttl"

        shacl_graph = create_shacl_shapes(str(self.skgif_path))
        shacl_graph.serialize(destination=output_file, format="turtle", encoding="utf-8")

        SH = Namespace("http://www.w3.org/ns/shacl#")
        FRAPO = Namespace("http://purl.org/cerif/frapo/")
        FOAF = Namespace("http://xmlns.com/foaf/0.1/")
        PRISM = Namespace("http://prismstandard.org/namespaces/basic/2.0/")
        XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

        grant_shape = URIRef(SHAPES_BASE + "grant/GrantShape")
        self.assertIn((grant_shape, RDF.type, SH.NodeShape), shacl_graph)

        grant_properties = list(shacl_graph.objects(grant_shape, SH.property))

        expected_properties = {
            'hasGrantNumber': {
                'path': FRAPO.hasGrantNumber,
                'datatype': XSD.string
            },
            'hasAcronym': {
                'path': FRAPO.hasAcronym,
                'nodeKind': SH.Literal
            },
            'hasCallIdentifier': {
                'path': FRAPO.hasCallIdentifier,
                'nodeKind': SH.Literal
            },
            'keyword': {
                'path': PRISM.keyword,
                'nodeKind': SH.Literal
            }
        }

        found_properties = set()
        for prop_shape in grant_properties:
            path = shacl_graph.value(prop_shape, SH.path)
            if path in [p['path'] for p in expected_properties.values()]:
                prop_name = [k for k, v in expected_properties.items() if v['path'] == path][0]
                found_properties.add(prop_name)

                if 'datatype' in expected_properties[prop_name]:
                    self.assertIn(
                        (prop_shape, SH.datatype, expected_properties[prop_name]['datatype']),
                        shacl_graph
                    )
                if 'nodeKind' in expected_properties[prop_name]:
                    self.assertIn(
                        (prop_shape, SH.nodeKind, expected_properties[prop_name]['nodeKind']),
                        shacl_graph
                    )

        self.assertEqual(found_properties, set(expected_properties.keys()))

        agent_shape = URIRef(SHAPES_BASE + "agent/AgentShape")
        self.assertIn((agent_shape, RDF.type, SH.NodeShape), shacl_graph)

        agent_properties = list(shacl_graph.objects(agent_shape, SH.property))

        name_found = False
        for prop_shape in agent_properties:
            path = shacl_graph.value(prop_shape, SH.path)
            if path == FOAF.name:
                name_found = True
                self.assertIn((prop_shape, SH.nodeKind, SH.Literal), shacl_graph)

        self.assertTrue(name_found)

    def test_opencitations_example_validation(self):
        examples_path = Path('examples/OpenCitations/oc_1.jsonld')
        if not examples_path.exists():
            self.skipTest("OpenCitations examples not available")

        shapes_graph = create_shacl_shapes(str(self.skgif_path))

        data_graph = Graph()
        with open(examples_path, 'r', encoding='utf-8') as f:
            jsonld_data = json.load(f)

        data_graph.parse(data=json.dumps(jsonld_data), format='json-ld')

        conforms, results_graph, results_text = validate(
            data_graph=data_graph,
            shacl_graph=shapes_graph,
            debug=False,
        )

        self.assertTrue(
            conforms,
            f"OpenCitations example data does not conform to SHACL shapes. Validation results:\n{results_text}"
        )

    def test_all_current_examples_validation(self):
        examples_path = Path('context/ver/current/samples')
        if not examples_path.exists():
            self.skipTest("Context submodule not available")

        shapes_graph = create_shacl_shapes(str(self.skgif_path))
        example_files = list(examples_path.glob('example-*.json'))

        for example_file in example_files:
            with self.subTest(example=example_file.name):
                data_graph = Graph()
                with open(example_file, 'r', encoding='utf-8') as f:
                    jsonld_data = json.load(f)

                data_graph.parse(data=json.dumps(jsonld_data), format='json-ld')

                conforms, results_graph, results_text = validate(
                    data_graph=data_graph,
                    shacl_graph=shapes_graph,
                    debug=False,
                )

                self.assertTrue(
                    conforms,
                    f"{example_file.name} does not conform to SHACL shapes. "
                    f"Validation results:\n{results_text}"
                )


class TestSingleFileOntology(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(dir=".")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_single_file_shapes(self):
        ttl_file = Path(self.temp_dir) / "test-ontology.ttl"
        with open(ttl_file, 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix ex: <http://example.org/ontology/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<http://example.org/ontology/test-onto> a owl:Ontology .

ex:Person a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:hasName -[1]-> rdfs:Literal
* ex:hasAddress -[0..1]-> ex:Address""" .

ex:Address a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:street -[1]-> rdfs:Literal""" .
''')

        shacl_graph = create_shacl_shapes(str(ttl_file))

        SH = Namespace("http://www.w3.org/ns/shacl#")
        shapes_base = "http://example.org/ontology/test-onto/shapes/"

        person_shape = URIRef(shapes_base + "PersonShape")
        address_shape = URIRef(shapes_base + "AddressShape")

        self.assertIn((person_shape, RDF.type, SH.NodeShape), shacl_graph)
        self.assertIn((address_shape, RDF.type, SH.NodeShape), shacl_graph)

        EX = Namespace("http://example.org/ontology/")
        self.assertIn((person_shape, SH.targetClass, EX.Person), shacl_graph)
        self.assertIsNone(shacl_graph.value(address_shape, SH.targetClass))

        person_props = list(shacl_graph.objects(person_shape, SH.property))
        self.assertEqual(len(person_props), 2)

        for prop_shape in person_props:
            path = shacl_graph.value(prop_shape, SH.path)
            if path == EX.hasAddress:
                self.assertIn((prop_shape, SH.node, address_shape), shacl_graph)

    def test_single_file_shapes_base_from_ontology_iri(self):
        ttl_file = Path(self.temp_dir) / "onto.ttl"
        with open(ttl_file, 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix ex: <http://example.org/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<https://w3id.org/dharc/ontology/chad-ap> a owl:Ontology .

ex:Thing a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:label -[1]-> rdfs:Literal""" .
''')

        shacl_graph = create_shacl_shapes(str(ttl_file))

        SH = Namespace("http://www.w3.org/ns/shacl#")
        shape_uri = URIRef("https://w3id.org/dharc/ontology/chad-ap/shapes/ThingShape")
        self.assertIn((shape_uri, RDF.type, SH.NodeShape), shacl_graph)

    def test_custom_shapes_base(self):
        ttl_file = Path(self.temp_dir) / "onto.ttl"
        with open(ttl_file, 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix ex: <http://example.org/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:Thing a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:label -[1]-> rdfs:Literal""" .
''')

        custom_base = "https://custom.example.org/shapes/"
        shacl_graph = create_shacl_shapes(str(ttl_file), shapes_base=custom_base)

        SH = Namespace("http://www.w3.org/ns/shacl#")
        shape_uri = URIRef(custom_base + "ThingShape")
        self.assertIn((shape_uri, RDF.type, SH.NodeShape), shacl_graph)

    def test_hyphenated_property_and_class_names(self):
        ttl_file = Path(self.temp_dir) / "hyphen-test.ttl"
        with open(ttl_file, 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix crm: <http://www.cidoc-crm.org/cidoc-crm/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://example.org/hyphen-onto> a owl:Ontology .

crm:E52_Time-Span a owl:Class ;
    dc:description """The properties that can be used with this class are:

* crm:P82a_begin_of_the_begin -[1]-> xsd:dateTime
* crm:P82b_end_of_the_end -[1]-> xsd:dateTime""" .

crm:E7_Activity a owl:Class ;
    dc:description """The properties that can be used with this class are:

* crm:P4_has_time-span -[1]-> crm:E52_Time-Span""" .
''')

        shacl_graph = create_shacl_shapes(str(ttl_file))

        SH = Namespace("http://www.w3.org/ns/shacl#")
        CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
        XSD_NS = Namespace("http://www.w3.org/2001/XMLSchema#")
        shapes_base = "http://example.org/hyphen-onto/shapes/"

        activity_shape = URIRef(shapes_base + "E7_ActivityShape")
        timespan_shape = URIRef(shapes_base + "E52_Time-SpanShape")

        self.assertIn((activity_shape, RDF.type, SH.NodeShape), shacl_graph)
        self.assertIn((timespan_shape, RDF.type, SH.NodeShape), shacl_graph)

        self.assertIn((activity_shape, SH.targetClass, CRM['E7_Activity']), shacl_graph)
        self.assertIsNone(shacl_graph.value(timespan_shape, SH.targetClass))

        activity_props = list(shacl_graph.objects(activity_shape, SH.property))
        self.assertEqual(len(activity_props), 1)
        prop_shape = activity_props[0]
        self.assertIn((prop_shape, SH.path, CRM['P4_has_time-span']), shacl_graph)
        self.assertIn((prop_shape, SH.node, timespan_shape), shacl_graph)

        timespan_props = list(shacl_graph.objects(timespan_shape, SH.property))
        self.assertEqual(len(timespan_props), 2)
        for prop_shape in timespan_props:
            self.assertIn((prop_shape, SH.datatype, XSD_NS.dateTime), shacl_graph)

    def test_undeclared_prefix_resolution(self):
        ttl_file = Path(self.temp_dir) / "undeclared-prefix.ttl"
        with open(ttl_file, 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<http://example.org/test-onto> a owl:Ontology .

<http://example.org/ns/MyClass> a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:myProp -[1]-> rdfs:Literal""" .

<http://example.org/ns/myProp> a owl:ObjectProperty .
''')

        shacl_graph = create_shacl_shapes(str(ttl_file))

        SH = Namespace("http://www.w3.org/ns/shacl#")
        shapes = list(shacl_graph.subjects(RDF.type, SH.NodeShape))
        self.assertEqual(len(shapes), 1)

        prop_shapes = list(shacl_graph.objects(shapes[0], SH.property))
        self.assertEqual(len(prop_shapes), 1)
        path = shacl_graph.value(prop_shapes[0], SH.path)
        self.assertEqual(str(path), "http://example.org/ns/myProp")

    def test_root_class_detection(self):
        ttl_file = Path(self.temp_dir) / "root-test.ttl"
        with open(ttl_file, 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix ex: <http://example.org/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:A a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:hasB -[1]-> ex:B
* ex:hasC -[0..N]-> ex:C""" .

ex:B a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:label -[1]-> rdfs:Literal""" .

ex:C a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:value -[1]-> rdfs:Literal""" .

ex:D a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:name -[1]-> rdfs:Literal""" .
''')

        shacl_graph = create_shacl_shapes(str(ttl_file))

        SH = Namespace("http://www.w3.org/ns/shacl#")
        EX = Namespace("http://example.org/")

        shapes = list(shacl_graph.subjects(RDF.type, SH.NodeShape))
        self.assertEqual(len(shapes), 4)

        target_classes = set()
        for shape in shapes:
            tc = shacl_graph.value(shape, SH.targetClass)
            if tc:
                target_classes.add(str(tc))

        self.assertEqual(target_classes, {str(EX.A), str(EX.D)})

    def test_single_file_no_ontology_iri(self):
        ttl_file = Path(self.temp_dir) / "no-iri.ttl"
        with open(ttl_file, 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix ex: <http://example.org/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:Thing a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:label -[1]-> rdfs:Literal""" .
''')

        shacl_graph = create_shacl_shapes(str(ttl_file))

        SH = Namespace("http://www.w3.org/ns/shacl#")
        shape_uri = URIRef("http://example.org/shapes/ThingShape")
        self.assertIn((shape_uri, RDF.type, SH.NodeShape), shacl_graph)

    def test_load_source_single_file(self):
        ttl_file = Path(self.temp_dir) / "single.ttl"
        with open(ttl_file, 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix ex: <http://example.org/> .

<http://example.org/my-onto> a owl:Ontology .

ex:TestClass a owl:Class .
''')

        modules, is_modular = _load_source(str(ttl_file))
        self.assertFalse(is_modular)
        self.assertEqual(list(modules.keys()), ["my-onto"])
        g = modules["my-onto"]
        EX = Namespace("http://example.org/")
        self.assertIn((EX.TestClass, RDF.type, OWL.Class), g)

    def test_url_loading(self):
        ttl_file = Path(self.temp_dir) / "url-sim.ttl"
        with open(ttl_file, 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix ex: <http://example.org/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<http://example.org/test-onto> a owl:Ontology .

ex:Item a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:name -[1]-> rdfs:Literal""" .
''')
        original_parse = Graph.parse

        def patched_parse(self_graph, source=None, **kwargs):
            if isinstance(source, str) and source.startswith('https://example.org/'):
                return original_parse(self_graph, str(ttl_file), format='turtle')
            return original_parse(self_graph, source, **kwargs)

        with unittest.mock.patch.object(Graph, 'parse', patched_parse):
            modules, is_modular = _load_source("https://example.org/ontology.ttl")
            self.assertFalse(is_modular)
            self.assertEqual(list(modules.keys()), ["test-onto"])
            g = modules["test-onto"]
            self.assertTrue(any(g.subjects(RDF.type, OWL.Class)))

    def test_main_with_single_file(self):
        ttl_file = Path(self.temp_dir) / "url-test.ttl"
        with open(ttl_file, 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix ex: <http://example.org/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:Thing a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:label -[1]-> rdfs:Literal""" .
''')

        output_file = Path(self.temp_dir) / "url_output.ttl"
        test_args = ['prog_name', str(ttl_file), str(output_file)]
        with unittest.mock.patch('sys.argv', test_args):
            from src.main import main
            main()

        self.assertTrue(output_file.exists())
        g = Graph()
        g.parse(output_file, format='turtle')
        SH = Namespace("http://www.w3.org/ns/shacl#")
        self.assertTrue(any(s for s in g.subjects(RDF.type, SH.NodeShape)))

    def test_main_with_shapes_base(self):
        ttl_file = Path(self.temp_dir) / "shapes-base-test.ttl"
        with open(ttl_file, 'w', encoding='utf-8') as f:
            f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix ex: <http://example.org/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:Thing a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:label -[1]-> rdfs:Literal""" .
''')

        output_file = Path(self.temp_dir) / "shapes_base_output.ttl"
        custom_base = "https://custom.example.org/my-shapes/"
        test_args = ['prog_name', str(ttl_file), str(output_file), '--shapes-base', custom_base]
        with unittest.mock.patch('sys.argv', test_args):
            from src.main import main
            main()

        g = Graph()
        g.parse(output_file, format='turtle')
        SH = Namespace("http://www.w3.org/ns/shacl#")
        shape_uri = URIRef(custom_base + "ThingShape")
        self.assertIn((shape_uri, RDF.type, SH.NodeShape), g)


class TestHelperFunctions(unittest.TestCase):
    def test_is_url(self):
        self.assertTrue(_is_url("https://example.org/ontology.ttl"))
        self.assertTrue(_is_url("http://example.org/ontology.ttl"))
        self.assertFalse(_is_url("/path/to/file.ttl"))
        self.assertFalse(_is_url("relative/path.ttl"))

    def test_get_ontology_iri(self):
        g = Graph()
        g.parse(data='''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
<http://example.org/my-onto> a owl:Ontology .
''', format='turtle')
        self.assertEqual(_get_ontology_iri(g), "http://example.org/my-onto")

    def test_get_ontology_iri_missing(self):
        g = Graph()
        g.parse(data='''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix ex: <http://example.org/> .
ex:Thing a owl:Class .
''', format='turtle')
        self.assertIsNone(_get_ontology_iri(g))

    def test_derive_module_name_from_iri(self):
        g = Graph()
        g.parse(data='''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
<https://w3id.org/dharc/ontology/chad-ap> a owl:Ontology .
''', format='turtle')
        self.assertEqual(_derive_module_name("irrelevant", g), "chad-ap")

    def test_derive_module_name_from_file(self):
        g = Graph()
        g.parse(data='@prefix owl: <http://www.w3.org/2002/07/owl#> .', format='turtle')
        self.assertEqual(_derive_module_name("/path/to/my-ontology.ttl", g), "my-ontology")

    def test_derive_module_name_from_url(self):
        g = Graph()
        g.parse(data='@prefix owl: <http://www.w3.org/2002/07/owl#> .', format='turtle')
        self.assertEqual(_derive_module_name("https://example.org/path/onto.ttl", g), "onto")

    def test_derive_shapes_base_from_iri(self):
        g = Graph()
        g.parse(data='''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
<https://w3id.org/dharc/ontology/chad-ap> a owl:Ontology .
''', format='turtle')
        self.assertEqual(_derive_shapes_base("irrelevant", g), "https://w3id.org/dharc/ontology/chad-ap/shapes/")

    def test_derive_shapes_base_fallback(self):
        g = Graph()
        g.parse(data='@prefix owl: <http://www.w3.org/2002/07/owl#> .', format='turtle')
        self.assertEqual(_derive_shapes_base("irrelevant", g), "http://example.org/shapes/")

    def test_detect_root_classes(self):
        g = Graph()
        g.parse(data='''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix ex: <http://example.org/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:Parent a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:hasChild -[0..N]-> ex:Child""" .

ex:Child a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:name -[1]-> rdfs:Literal""" .

ex:Standalone a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:value -[1]-> rdfs:Literal""" .
''', format='turtle')

        described = {
            "http://example.org/Parent",
            "http://example.org/Child",
            "http://example.org/Standalone",
        }
        roots = _detect_root_classes(g, described)
        self.assertEqual(roots, {"http://example.org/Parent", "http://example.org/Standalone"})

    def test_extract_prefixes_from_literals(self):
        g = Graph()
        g.parse(data='''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .

<http://example.org/onto> a owl:Ontology ;
    dc:description """Some text with prefix declarations:

    @prefix crm: <http://www.cidoc-crm.org/cidoc-crm/> .
    @prefix lrmoo: <http://iflastandards.info/ns/lrm/lrmoo/> .
""" .
''', format='turtle')

        prefixes = _extract_prefixes_from_literals(g)
        self.assertEqual(prefixes, {
            "crm": "http://www.cidoc-crm.org/cidoc-crm/",
            "lrmoo": "http://iflastandards.info/ns/lrm/lrmoo/",
        })

    def test_literal_prefix_resolution_in_shapes(self):
        ttl_file = Path(tempfile.mkdtemp(dir=".")) / "literal-prefix.ttl"
        try:
            with open(ttl_file, 'w', encoding='utf-8') as f:
                f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<http://example.org/test> a owl:Ontology ;
    dc:description """Prefixes used:

    @prefix crm: <http://www.cidoc-crm.org/cidoc-crm/> .
    @prefix lrmoo: <http://iflastandards.info/ns/lrm/lrmoo/> .
""" .

<http://iflastandards.info/ns/lrm/lrmoo/F1_Work> a owl:Class ;
    dc:description """The properties that can be used with this class are:

* lrmoo:R3_is_realized_in -[1..N]-> rdfs:Literal""" .
''')

            shacl_graph = create_shacl_shapes(str(ttl_file))

            SH = Namespace("http://www.w3.org/ns/shacl#")
            shapes = list(shacl_graph.subjects(RDF.type, SH.NodeShape))
            self.assertEqual(len(shapes), 1)

            prop_shapes = list(shacl_graph.objects(shapes[0], SH.property))
            self.assertEqual(len(prop_shapes), 1)
            path = shacl_graph.value(prop_shapes[0], SH.path)
            self.assertEqual(str(path), "http://iflastandards.info/ns/lrm/lrmoo/R3_is_realized_in")
        finally:
            shutil.rmtree(ttl_file.parent)

    def test_unqualified_target_name(self):
        ttl_file = Path(tempfile.mkdtemp(dir=".")) / "unqualified.ttl"
        try:
            with open(ttl_file, 'w', encoding='utf-8') as f:
                f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix crm: <http://www.cidoc-crm.org/cidoc-crm/> .

<http://example.org/test> a owl:Ontology .

crm:E7_Activity a owl:Class ;
    dc:description """The properties that can be used with this class are:

* crm:P2_has_type -[1]-> crm:E55_Type
* crm:P32_used_general_technique -[0..N]-> E55_Type""" .

crm:E55_Type a owl:Class ;
    dc:description """The properties that can be used with this class are:

* crm:P1_is_identified_by -[0..N]-> crm:E41_Appellation""" .

crm:E41_Appellation a owl:Class ;
    dc:description """The properties that can be used with this class are:

* crm:P190_has_symbolic_content -[0..1]-> rdfs:Literal""" .
''')

            shacl_graph = create_shacl_shapes(str(ttl_file))

            SH = Namespace("http://www.w3.org/ns/shacl#")
            CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
            shapes_base = "http://example.org/test/shapes/"
            type_shape = URIRef(shapes_base + "E55_TypeShape")

            activity_shape = URIRef(shapes_base + "E7_ActivityShape")
            activity_props = list(shacl_graph.objects(activity_shape, SH.property))
            self.assertEqual(len(activity_props), 2)

            for prop_shape in activity_props:
                path = shacl_graph.value(prop_shape, SH.path)
                if path == CRM.P32_used_general_technique:
                    self.assertIn((prop_shape, SH.node, type_shape), shacl_graph)
        finally:
            shutil.rmtree(ttl_file.parent)


if __name__ == '__main__':
    unittest.main()
