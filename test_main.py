import json
import shutil
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, OWL
from src.main import create_shacl_shapes, get_ontology_path, load_ontology


class TestTTLToSHACL(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(dir=".")
        self.test_data = '''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix ex: <http://example.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:TestClass a owl:Class ;
    dc:description """The properties that can be used with this class are:
- ex:stringProp -[1]-> xsd:string
- ex:intProp -[0..1]-> xsd:integer
- ex:objectProp -[1..*]-> ex:OtherClass
- ex:literalProp -[1]-> rdfs:Literal
""" .

ex:OtherClass a owl:Class .
'''
        self.input_file = Path(self.temp_dir) / "test.ttl"
        with open(self.input_file, 'w', encoding='utf-8') as f:
            f.write(self.test_data)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_basic_shape_creation(self):
        shacl_graph = create_shacl_shapes(self.input_file)
        output_file = Path(self.temp_dir) / "basic_shape.ttl"
        shacl_graph.serialize(destination=output_file, format="turtle", encoding="utf-8")
        
        SH = Namespace("http://www.w3.org/ns/shacl#")
        EX = Namespace("http://example.org/")
        shape_uri = URIRef("http://example.org/TestClassShape")
        
        self.assertIn((shape_uri, RDF.type, SH.NodeShape), shacl_graph)
        self.assertIn((shape_uri, SH.targetClass, EX.TestClass), shacl_graph)

    def test_property_constraints(self):
        shacl_graph = create_shacl_shapes(self.input_file)
        output_file = Path(self.temp_dir) / "property_constraints.ttl"
        shacl_graph.serialize(destination=output_file, format="turtle", encoding="utf-8")
        
        SH = Namespace("http://www.w3.org/ns/shacl#")
        EX = Namespace("http://example.org/")
        XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
        shape_uri = URIRef("http://example.org/TestClassShape")
        
        property_shapes = list(shacl_graph.objects(shape_uri, SH.property, unique=True))
        self.assertEqual(len(property_shapes), 4)
        
        props_found = {
            'stringProp': False,
            'intProp': False,
            'objectProp': False,
            'literalProp': False
        }
        
        for prop_shape in property_shapes:
            path = shacl_graph.value(prop_shape, SH.path)
            if path == EX.stringProp:
                props_found['stringProp'] = True
                self.assertIn((prop_shape, SH.datatype, XSD.string), shacl_graph)
                self.assertIn((prop_shape, SH.minCount, Literal(1)), shacl_graph)
                self.assertIn((prop_shape, SH.maxCount, Literal(1)), shacl_graph)
            elif path == EX.intProp:
                props_found['intProp'] = True
                self.assertIn((prop_shape, SH.datatype, XSD.integer), shacl_graph)
                self.assertIn((prop_shape, SH.maxCount, Literal(1)), shacl_graph)
            elif path == EX.objectProp:
                props_found['objectProp'] = True
                # self.assertIn((prop_shape, SH["class"], EX.OtherClass), shacl_graph)
                self.assertIn((prop_shape, SH.minCount, Literal(1)), shacl_graph)
            elif path == EX.literalProp:
                props_found['literalProp'] = True
                self.assertIn((prop_shape, SH.nodeKind, SH.Literal), shacl_graph)
                self.assertIn((prop_shape, SH.minCount, Literal(1)), shacl_graph)
                self.assertIn((prop_shape, SH.maxCount, Literal(1)), shacl_graph)
        
        self.assertTrue(all(props_found.values()))

    def test_no_description(self):
        no_desc_file = Path(self.temp_dir) / "no_desc.ttl"
        with open(no_desc_file, 'w', encoding='utf-8') as f:
            f.write("""
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix ex: <http://example.org/> .

ex:NoDescClass a owl:Class .
""")
            
        shacl_graph = create_shacl_shapes(no_desc_file)
        output_file = Path(self.temp_dir) / "no_description.ttl"
        shacl_graph.serialize(destination=output_file, format="turtle", encoding="utf-8")
        
        self.assertEqual(len(list(shacl_graph.subjects(RDF.type, URIRef("http://www.w3.org/ns/shacl#NodeShape")))), 0)

    def test_main_function(self):
        input_file = self.input_file
        output_file = Path(self.temp_dir) / "test_main_output.ttl"
        
        test_args = ['prog_name', '--input', str(input_file), str(output_file)]
        with unittest.mock.patch('sys.argv', test_args):
            from src.main import main
            main()
        
        self.assertTrue(output_file.exists())
        g = Graph()
        g.parse(output_file, format='turtle')
        
        SH = Namespace("http://www.w3.org/ns/shacl#")
        self.assertTrue(any(s for s in g.subjects(RDF.type, SH.NodeShape)))

    def test_get_ontology_path_with_version(self):
        """Test get_ontology_path with a specific version (pre 1.0.1)"""
        version = "1.0.0"
        expected_path = str(Path("data-model") / "ontology" / "1.0.0" / "skg-o.ttl")
        actual_path = get_ontology_path(version)
        self.assertEqual(actual_path, expected_path)

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

    def test_load_ontology_single_file(self):
        """Test loading a single TTL file (pre 1.0.1)"""
        input_file = self.input_file
        g = load_ontology(str(input_file))
        self.assertTrue(isinstance(g, Graph))
        self.assertTrue(len(g) > 0)
        
        # Verify we can find our test class
        EX = Namespace("http://example.org/")
        self.assertIn((EX.TestClass, RDF.type, OWL.Class), g)

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
                
        # 1. Test Grant shape
        grant_shape = URIRef("http://purl.org/cerif/frapo/GrantShape")
        self.assertIn((grant_shape, RDF.type, SH.NodeShape), shacl_graph)
        
        # Verifichiamo invece che ci siano i targetSubjectsOf appropriati
        has_grant_number = FRAPO.hasGrantNumber
        # self.assertIn((grant_shape, SH.targetSubjectsOf, has_grant_number), shacl_graph)
        
        # Get all property shapes for Grant
        grant_properties = list(shacl_graph.objects(grant_shape, SH.property))
        
        # Test specific property constraints for Grant
        expected_properties = {
            'hasGrantNumber': {
                'path': FRAPO.hasGrantNumber,
                'datatype': XSD.string,
                'maxCount': 1
            },
            'hasAcronym': {
                'path': FRAPO.hasAcronym,
                'nodeKind': SH.Literal,
                'maxCount': 1
            },
            'hasCallIdentifier': {
                'path': FRAPO.hasCallIdentifier,
                'nodeKind': SH.Literal,
                'maxCount': 1
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
                    self.assertIn(
                        (prop_shape, SH.maxCount, Literal(expected_properties[prop_name]['maxCount'])), 
                        shacl_graph
                    )
        
        # Verify all expected properties were found
        self.assertEqual(found_properties, set(expected_properties.keys()))
        
        # 2. Test Agent shape
        agent_shape = URIRef("http://xmlns.com/foaf/0.1/AgentShape")
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
                self.assertIn((prop_shape, SH.maxCount, Literal(1)), shacl_graph)
        
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

if __name__ == '__main__':
    unittest.main()