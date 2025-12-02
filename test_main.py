import json
import shutil
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, OWL
from src.main import create_shacl_shapes, get_ontology_path, load_ontology, load_ontology_by_module, SHAPES_BASE


class TestTTLToSHACL(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(dir=".")

        self.modular_dir = Path(self.temp_dir) / "modular"
        agent_dir = self.modular_dir / "agent"
        agent_dir.mkdir(parents=True)

        # Real data from data-model/ontology/current/agent/skg-o.ttl
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
        output_file = Path(self.temp_dir) / "basic_shape.ttl"
        shacl_graph.serialize(destination=output_file, format="turtle", encoding="utf-8")

        SH = Namespace("http://www.w3.org/ns/shacl#")
        FOAF = Namespace("http://xmlns.com/foaf/0.1/")
        shape_uri = URIRef(SHAPES_BASE + "agent/AgentShape")

        self.assertIn((shape_uri, RDF.type, SH.NodeShape), shacl_graph)
        # Agent is a root class, so it should have targetClass
        self.assertIn((shape_uri, SH.targetClass, FOAF.Agent), shacl_graph)

    def test_property_constraints(self):
        """Test property constraints using real ontology data."""
        shacl_graph = create_shacl_shapes(self.modular_dir)

        SH = Namespace("http://www.w3.org/ns/shacl#")
        FOAF = Namespace("http://xmlns.com/foaf/0.1/")
        DATACITE = Namespace("http://purl.org/spar/datacite/")
        XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

        # Test AgentShape (root class)
        agent_shape = URIRef(SHAPES_BASE + "agent/AgentShape")
        agent_props = list(shacl_graph.objects(agent_shape, SH.property, unique=True))
        self.assertEqual(len(agent_props), 2)

        # Test IdentifierShape (non-root class)
        identifier_shape = URIRef(SHAPES_BASE + "agent/IdentifierShape")
        self.assertIn((identifier_shape, RDF.type, SH.NodeShape), shacl_graph)
        # Non-root class should NOT have targetClass
        self.assertIsNone(shacl_graph.value(identifier_shape, SH.targetClass))

        for prop_shape in agent_props:
            path = shacl_graph.value(prop_shape, SH.path)
            if path == DATACITE.hasIdentifier:
                # Identifier has a shape, so sh:node should be used
                self.assertIn((prop_shape, SH.node, identifier_shape), shacl_graph)
            elif path == FOAF.name:
                # rdfs:Literal -> sh:nodeKind sh:Literal
                self.assertIn((prop_shape, SH.nodeKind, SH.Literal), shacl_graph)
                self.assertIn((prop_shape, SH.maxCount, Literal(1, datatype=XSD.integer)), shacl_graph)

        # Test IdentifierShape properties
        identifier_props = list(shacl_graph.objects(identifier_shape, SH.property, unique=True))
        self.assertEqual(len(identifier_props), 2)

        LITERAL = Namespace("http://www.essepuntato.it/2010/06/literalreification/")
        for prop_shape in identifier_props:
            path = shacl_graph.value(prop_shape, SH.path)
            if path == DATACITE.usesIdentifierScheme:
                # IdentifierScheme has no description -> sh:nodeKind sh:BlankNodeOrIRI
                self.assertIn((prop_shape, SH.nodeKind, SH.BlankNodeOrIRI), shacl_graph)
                self.assertIn((prop_shape, SH.minCount, Literal(1, datatype=XSD.integer)), shacl_graph)
                self.assertIn((prop_shape, SH.maxCount, Literal(1, datatype=XSD.integer)), shacl_graph)
            elif path == LITERAL.hasLiteralValue:
                self.assertIn((prop_shape, SH.nodeKind, SH.Literal), shacl_graph)
                self.assertIn((prop_shape, SH.minCount, Literal(1, datatype=XSD.integer)), shacl_graph)
                self.assertIn((prop_shape, SH.maxCount, Literal(1, datatype=XSD.integer)), shacl_graph)

        # IdentifierScheme should NOT have a shape (no description)
        scheme_shape = URIRef(SHAPES_BASE + "agent/IdentifierSchemeShape")
        self.assertNotIn((scheme_shape, RDF.type, SH.NodeShape), shacl_graph)

    def test_no_description(self):
        # Create modular structure with class without description
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
        output_file = Path(self.temp_dir) / "no_description.ttl"
        shacl_graph.serialize(destination=output_file, format="turtle", encoding="utf-8")

        self.assertEqual(len(list(shacl_graph.subjects(RDF.type, URIRef("http://www.w3.org/ns/shacl#NodeShape")))), 0)

    def test_main_function(self):
        output_file = Path(self.temp_dir) / "test_main_output.ttl"

        test_args = ['prog_name', '--input', str(self.modular_dir), str(output_file)]
        with unittest.mock.patch('sys.argv', test_args):
            from src.main import main
            main()

        self.assertTrue(output_file.exists())
        g = Graph()
        g.parse(output_file, format='turtle')

        SH = Namespace("http://www.w3.org/ns/shacl#")
        self.assertTrue(any(s for s in g.subjects(RDF.type, SH.NodeShape)))

    def test_get_ontology_path_current(self):
        """Test get_ontology_path with current version (1.0.1+)"""
        expected_path = str(Path("data-model") / "ontology" / "current")
        actual_path = get_ontology_path()
        self.assertEqual(actual_path, expected_path)

    def test_get_ontology_path_1_0_1(self):
        """Test get_ontology_path with version 1.0.1"""
        version = "1.0.1"
        expected_path = str(Path("data-model") / "ontology" / "1.0.1")
        actual_path = get_ontology_path(version)
        self.assertEqual(actual_path, expected_path)

    def test_load_ontology_modular(self):
        """Test loading modular TTL files (1.0.1+)"""
        # Create a temporary modular structure
        base_dir = Path(self.temp_dir) / "ontology" / "test_version"
        agent_dir = base_dir / "agent"
        agent_dir.mkdir(parents=True)

        # Create a test TTL file in the agent module
        agent_ttl = agent_dir / "skg-o.ttl"
        with open(agent_ttl, 'w', encoding='utf-8') as f:
            f.write("""
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix ex: <http://example.org/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .

foaf:Agent a owl:Class .
""")

        # Create another module directory and TTL file
        venue_dir = base_dir / "venue"
        venue_dir.mkdir()
        venue_ttl = venue_dir / "skg-o.ttl"
        with open(venue_ttl, 'w', encoding='utf-8') as f:
            f.write("""
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix ex: <http://example.org/> .

ex:Venue a owl:Class .
""")

        # Create a resources directory that should be ignored
        resources_dir = base_dir / "resources"
        resources_dir.mkdir()

        # Test loading the modular structure
        g = load_ontology(str(base_dir))

        # Verify both modules were loaded
        FOAF = Namespace("http://xmlns.com/foaf/0.1/")
        EX = Namespace("http://example.org/")

        self.assertIn((FOAF.Agent, RDF.type, OWL.Class), g)
        self.assertIn((EX.Venue, RDF.type, OWL.Class), g)

    def test_load_ontology_single_file(self):
        """Test loading a single TTL file directly (legacy support)"""
        # Create a single TTL file
        single_ttl = Path(self.temp_dir) / "single_ontology.ttl"
        with open(single_ttl, 'w', encoding='utf-8') as f:
            f.write("""
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix ex: <http://example.org/> .

ex:TestClass a owl:Class .
""")

        # Test loading the single file
        g = load_ontology(str(single_ttl))

        # Verify the class was loaded
        EX = Namespace("http://example.org/")
        self.assertIn((EX.TestClass, RDF.type, OWL.Class), g)

    def test_load_ontology_by_module_with_file(self):
        """Test load_ontology_by_module raises error when given a file path"""

        single_ttl = Path(self.temp_dir) / "single_ontology.ttl"
        with open(single_ttl, 'w', encoding='utf-8') as f:
            f.write("""
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix ex: <http://example.org/> .

ex:TestClass a owl:Class .
""")

        with self.assertRaises(ValueError) as context:
            load_ontology_by_module(str(single_ttl))

        self.assertIn("Single-file ontologies are not supported", str(context.exception))

    def test_current_ontology_conversion(self):
        """Test the conversion of the current ontology version to SHACL shapes"""
        input_path = get_ontology_path()  # This now returns the directory path
        output_file = Path(self.temp_dir) / "current_ontology_shapes.ttl"
        
        shacl_graph = create_shacl_shapes(input_path)
        shacl_graph.serialize(destination=output_file, format="turtle", encoding="utf-8")
        
        SH = Namespace("http://www.w3.org/ns/shacl#")
        FRAPO = Namespace("http://purl.org/cerif/frapo/")
        FOAF = Namespace("http://xmlns.com/foaf/0.1/")
        PRISM = Namespace("http://prismstandard.org/namespaces/basic/2.0/")
        XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
                
        # 1. Test Grant shape (now in grant module namespace)
        grant_shape = URIRef(SHAPES_BASE + "grant/GrantShape")
        self.assertIn((grant_shape, RDF.type, SH.NodeShape), shacl_graph)
                
        # Get all property shapes for Grant
        grant_properties = list(shacl_graph.objects(grant_shape, SH.property))
        
        # Test specific property constraints for Grant
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
                if 'maxCount' in expected_properties[prop_name]:
                    max_count_value = shacl_graph.value(prop_shape, SH.maxCount)
                    self.assertEqual(
                        max_count_value,
                        Literal(expected_properties[prop_name]['maxCount'], datatype=XSD.integer)
                    )
        
        # Verify all expected properties were found
        self.assertEqual(found_properties, set(expected_properties.keys()))
        
        # 2. Test Agent shape (now in agent module namespace)
        agent_shape = URIRef(SHAPES_BASE + "agent/AgentShape")
        self.assertIn((agent_shape, RDF.type, SH.NodeShape), shacl_graph)
        
        # self.assertIn((agent_shape, SH.targetSubjectsOf, FOAF.name), shacl_graph)
        
        # Get all property shapes for Agent
        agent_properties = list(shacl_graph.objects(agent_shape, SH.property))
        
        # Test name property for Agent
        name_found = False
        for prop_shape in agent_properties:
            path = shacl_graph.value(prop_shape, SH.path)
            if path == FOAF.name:
                name_found = True
                self.assertIn((prop_shape, SH.nodeKind, SH.Literal), shacl_graph)
                # maxCount not expected for properties with [0..N] cardinality
        
        self.assertTrue(name_found, "foaf:name property shape not found for Agent")

    def test_opencitations_example_validation(self):
        """Test that the OpenCitations example data validates against the SHACL shapes"""
        shapes_graph = create_shacl_shapes(Path(get_ontology_path()))
        
        data_graph = Graph()
        with open('examples/OpenCitations/oc_1.jsonld', 'r', encoding='utf-8') as f:
            jsonld_data = json.load(f)
        
        data_graph.parse(data=json.dumps(jsonld_data), format='json-ld')

        # Test basic structural expectations
        # Verifichiamo la presenza delle proprietà chiave invece dei tipi
        DCTERMS = Namespace("http://purl.org/dc/terms/")
        self.assertTrue(any(data_graph.subjects(DCTERMS.title, None)), 
                       "No entities with title found in the data")
        
        FOAF = Namespace("http://xmlns.com/foaf/0.1/")
        self.assertTrue(any(data_graph.subjects(FOAF.name, None)), 
                       "No entities with name found in the data")

        # Validate with inference enabled
        conforms, results_graph, results_text = validate(
            data_graph=data_graph,
            shacl_graph=shapes_graph,
            debug=False,
        )
        
        if not conforms:
            print("\nValidation Results:")
            print(results_text)
        
        self.assertTrue(
            conforms, 
            f"OpenCitations example data does not conform to SHACL shapes. Validation results:\n{results_text}"
        )
        

    def test_all_current_examples_validation(self):
        """Test all example files in the current version folder"""
        shapes_graph = create_shacl_shapes(Path(get_ontology_path()))
        examples_path = Path('context/ver/current/samples')
        
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
                
                if not conforms:
                    print(f"\n{example_file.name} Validation Results:")
                    print(results_text)
                
                self.assertTrue(
                    conforms, 
                    f"{example_file.name} does not conform to SHACL shapes. "
                    f"Validation results:\n{results_text}"
                )

    def test_get_ontology_path_invalid_version(self):
        """Test get_ontology_path with an invalid version"""
        with self.assertRaises(ValueError) as context:
            get_ontology_path("invalid_version")

        expected_path = Path("data-model/ontology/invalid_version")
        self.assertIn(f"Ontology version invalid_version not found at {expected_path}", str(context.exception))

    def test_get_ontology_path_file_not_directory(self):
        """Test get_ontology_path when path exists but is a file, not directory"""

        test_version_file = Path("data-model/ontology/_test_file_version_")
        try:
            test_version_file.write_text("# This is a file, not a directory")

            with self.assertRaises(ValueError) as context:
                get_ontology_path("_test_file_version_")

            self.assertIn("Single-file ontologies are not supported", str(context.exception))
        finally:
            if test_version_file.exists():
                test_version_file.unlink()

    def test_main_with_invalid_version(self):
        """Test main function with an invalid version"""
        output_file = Path(self.temp_dir) / "test_output.ttl"
        
        test_args = ['prog_name', '--version', 'invalid_version', str(output_file)]
        with unittest.mock.patch('sys.argv', test_args):
            with unittest.mock.patch('argparse.ArgumentParser.error') as mock_error:
                from src.main import main
                main()
                # Verify that error was called with the correct message
                mock_error.assert_called_once()
                error_msg = mock_error.call_args[0][0]
                expected_path = Path("data-model/ontology/invalid_version")
                self.assertIn(f"Ontology version invalid_version not found at {expected_path}", error_msg)

    def test_empty_property_description(self):
        """Test handling of empty property descriptions and whitespace-only properties"""
        # Create modular structure
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

        # This should not raise any exceptions
        shacl_graph = create_shacl_shapes(test_dir)

        # Verify we got the expected number of property shapes
        SH = Namespace("http://www.w3.org/ns/shacl#")
        shape_uri = URIRef(SHAPES_BASE + "agent/AgentShape")
        property_shapes = list(shacl_graph.objects(shape_uri, SH.property))

        # Should have 2 properties, skipping the empty ones
        self.assertEqual(len(property_shapes), 2)

        # Verify the properties we expect are present
        FOAF = Namespace("http://xmlns.com/foaf/0.1/")
        properties_found = set()
        for prop_shape in property_shapes:
            path = shacl_graph.value(prop_shape, SH.path)
            if path in [FOAF.name, FOAF.mbox]:
                properties_found.add(path)

        self.assertEqual(len(properties_found), 2, "Not all expected properties were found")

    def test_class_with_non_property_description(self):
        """Test handling of class with description that doesn't contain property info (line 137)"""

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
        self.assertEqual(len(shapes), 0, "No shapes should be created for class without property description")

    def test_invalid_property_format(self):
        """Test that invalid property format raises ValueError (line 155)"""
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
        """Test that unknown property prefix raises ValueError (line 162)"""
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
        """Test that unknown target prefix raises ValueError (line 183)"""
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


if __name__ == '__main__':
    unittest.main()