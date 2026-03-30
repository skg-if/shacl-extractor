# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelomas@gmail.com>
#
# SPDX-License-Identifier: ISC

from pathlib import Path
from unittest.mock import patch

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import RDF, OWL

from src.main import (
    SHAPES_BASE,
    _load_source,
    create_shacl_shapes,
)


def test_single_file_shapes(temp_dir):
    ttl_file = Path(temp_dir) / "test-ontology.ttl"
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

    assert (person_shape, RDF.type, SH.NodeShape) in shacl_graph
    assert (address_shape, RDF.type, SH.NodeShape) in shacl_graph

    EX = Namespace("http://example.org/ontology/")
    assert (person_shape, SH.targetClass, EX.Person) in shacl_graph
    assert shacl_graph.value(address_shape, SH.targetClass) is None

    person_props = list(shacl_graph.objects(person_shape, SH.property))
    assert len(person_props) == 2

    for prop_shape in person_props:
        path = shacl_graph.value(prop_shape, SH.path)
        if path == EX.hasAddress:
            assert (prop_shape, SH.node, address_shape) in shacl_graph


def test_single_file_shapes_base_from_ontology_iri(temp_dir):
    ttl_file = Path(temp_dir) / "onto.ttl"
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
    assert (shape_uri, RDF.type, SH.NodeShape) in shacl_graph


def test_custom_shapes_base(temp_dir):
    ttl_file = Path(temp_dir) / "onto.ttl"
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
    assert (shape_uri, RDF.type, SH.NodeShape) in shacl_graph


def test_hyphenated_property_and_class_names(temp_dir):
    ttl_file = Path(temp_dir) / "hyphen-test.ttl"
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

    assert (activity_shape, RDF.type, SH.NodeShape) in shacl_graph
    assert (timespan_shape, RDF.type, SH.NodeShape) in shacl_graph

    assert (activity_shape, SH.targetClass, CRM['E7_Activity']) in shacl_graph
    assert shacl_graph.value(timespan_shape, SH.targetClass) is None

    activity_props = list(shacl_graph.objects(activity_shape, SH.property))
    assert len(activity_props) == 1
    prop_shape = activity_props[0]
    assert (prop_shape, SH.path, CRM['P4_has_time-span']) in shacl_graph
    assert (prop_shape, SH.node, timespan_shape) in shacl_graph

    timespan_props = list(shacl_graph.objects(timespan_shape, SH.property))
    assert len(timespan_props) == 2
    for prop_shape in timespan_props:
        assert (prop_shape, SH.datatype, XSD_NS.dateTime) in shacl_graph


def test_undeclared_prefix_resolution(temp_dir):
    ttl_file = Path(temp_dir) / "undeclared-prefix.ttl"
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
    assert len(shapes) == 1

    prop_shapes = list(shacl_graph.objects(shapes[0], SH.property))
    assert len(prop_shapes) == 1
    path = shacl_graph.value(prop_shapes[0], SH.path)
    assert str(path) == "http://example.org/ns/myProp"


def test_root_class_detection(temp_dir):
    ttl_file = Path(temp_dir) / "root-test.ttl"
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
    assert len(shapes) == 4

    target_classes = set()
    for shape in shapes:
        tc = shacl_graph.value(shape, SH.targetClass)
        if tc:
            target_classes.add(str(tc))

    assert target_classes == {str(EX.A), str(EX.D)}


def test_explicit_root_classes(temp_dir):
    ttl_file = Path(temp_dir) / "root-explicit.ttl"
    with open(ttl_file, 'w', encoding='utf-8') as f:
        f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix ex: <http://example.org/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:A a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:hasB -[1]-> ex:B""" .

ex:B a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:label -[1]-> rdfs:Literal""" .
''')

    root_classes = {"test": "http://example.org/B"}
    shacl_graph = create_shacl_shapes(str(ttl_file), root_classes=root_classes)

    SH = Namespace("http://www.w3.org/ns/shacl#")
    EX = Namespace("http://example.org/")

    for shape in shacl_graph.subjects(RDF.type, SH.NodeShape):
        tc = shacl_graph.value(shape, SH.targetClass)
        if tc:
            assert tc == EX.B
        else:
            assert (shape, SH.targetClass, EX.A) not in shacl_graph


def test_single_file_no_ontology_iri(temp_dir):
    ttl_file = Path(temp_dir) / "no-iri.ttl"
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
    assert (shape_uri, RDF.type, SH.NodeShape) in shacl_graph


def test_load_source_single_file(temp_dir):
    ttl_file = Path(temp_dir) / "single.ttl"
    with open(ttl_file, 'w', encoding='utf-8') as f:
        f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix ex: <http://example.org/> .

<http://example.org/my-onto> a owl:Ontology .

ex:TestClass a owl:Class .
''')

    modules, is_modular = _load_source(str(ttl_file))
    assert not is_modular
    assert list(modules.keys()) == ["my-onto"]
    g = modules["my-onto"]
    EX = Namespace("http://example.org/")
    assert (EX.TestClass, RDF.type, OWL.Class) in g


def test_url_loading(temp_dir):
    ttl_file = Path(temp_dir) / "url-sim.ttl"
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

    with patch.object(Graph, 'parse', patched_parse):
        modules, is_modular = _load_source("https://example.org/ontology.ttl")
        assert not is_modular
        assert list(modules.keys()) == ["test-onto"]
        g = modules["test-onto"]
        assert any(g.subjects(RDF.type, OWL.Class))


def test_main_with_single_file(temp_dir):
    ttl_file = Path(temp_dir) / "url-test.ttl"
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

    output_file = Path(temp_dir) / "url_output.ttl"
    test_args = ['prog_name', str(ttl_file), str(output_file)]
    with patch('sys.argv', test_args):
        from src.main import main
        main()

    assert output_file.exists()
    g = Graph()
    g.parse(output_file, format='turtle')
    SH = Namespace("http://www.w3.org/ns/shacl#")
    assert any(s for s in g.subjects(RDF.type, SH.NodeShape))


def test_main_with_shapes_base(temp_dir):
    ttl_file = Path(temp_dir) / "shapes-base-test.ttl"
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

    output_file = Path(temp_dir) / "shapes_base_output.ttl"
    custom_base = "https://custom.example.org/my-shapes/"
    test_args = ['prog_name', str(ttl_file), str(output_file), '--shapes-base', custom_base]
    with patch('sys.argv', test_args):
        from src.main import main
        main()

    g = Graph()
    g.parse(output_file, format='turtle')
    SH = Namespace("http://www.w3.org/ns/shacl#")
    shape_uri = URIRef(custom_base + "ThingShape")
    assert (shape_uri, RDF.type, SH.NodeShape) in g


def test_controlled_vocabulary_prefixed(temp_dir):
    ttl_file = Path(temp_dir) / "cv-prefixed.ttl"
    with open(ttl_file, 'w', encoding='utf-8') as f:
        f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix datacite: <http://purl.org/spar/datacite/> .
@prefix literal: <http://www.essepuntato.it/2010/06/literalreification/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<http://example.org/onto> a owl:Ontology .

datacite:Identifier a owl:Class ;
    dc:description """The properties that can be used with this class are:

* datacite:usesIdentifierScheme -[1]-> {datacite:doi datacite:isbn datacite:orcid}
* literal:hasLiteralValue -[1]-> rdfs:Literal""" .
''')

    shacl_graph = create_shacl_shapes(ttl_file)

    SH = Namespace("http://www.w3.org/ns/shacl#")
    DATACITE = Namespace("http://purl.org/spar/datacite/")
    XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

    shapes_base = "http://example.org/onto/shapes/"
    identifier_shape = URIRef(shapes_base + "IdentifierShape")
    assert (identifier_shape, RDF.type, SH.NodeShape) in shacl_graph

    for prop_shape in shacl_graph.objects(identifier_shape, SH.property):
        path = shacl_graph.value(prop_shape, SH.path)
        if path == DATACITE.usesIdentifierScheme:
            assert (prop_shape, SH.minCount, Literal(1, datatype=XSD.integer)) in shacl_graph
            assert (prop_shape, SH.maxCount, Literal(1, datatype=XSD.integer)) in shacl_graph
            in_list = shacl_graph.value(prop_shape, SH['in'])
            assert in_list is not None
            items = list(Collection(shacl_graph, in_list))
            assert items == [DATACITE.doi, DATACITE.isbn, DATACITE.orcid]
            assert shacl_graph.value(prop_shape, SH.nodeKind) is None
            assert shacl_graph.value(prop_shape, SH.node) is None


def test_controlled_vocabulary_absolute_uris(temp_dir):
    ttl_file = Path(temp_dir) / "cv-absolute.ttl"
    with open(ttl_file, 'w', encoding='utf-8') as f:
        f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix datacite: <http://purl.org/spar/datacite/> .
@prefix literal: <http://www.essepuntato.it/2010/06/literalreification/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<http://example.org/onto> a owl:Ontology .

datacite:Identifier a owl:Class ;
    dc:description """The properties that can be used with this class are:

* datacite:usesIdentifierScheme -[1]-> {http://purl.org/spar/datacite/doi http://purl.org/spar/datacite/isbn http://purl.org/spar/datacite/orcid}
* literal:hasLiteralValue -[1]-> rdfs:Literal""" .
''')

    shacl_graph = create_shacl_shapes(ttl_file)

    SH = Namespace("http://www.w3.org/ns/shacl#")
    DATACITE = Namespace("http://purl.org/spar/datacite/")
    XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

    shapes_base = "http://example.org/onto/shapes/"
    identifier_shape = URIRef(shapes_base + "IdentifierShape")
    assert (identifier_shape, RDF.type, SH.NodeShape) in shacl_graph

    for prop_shape in shacl_graph.objects(identifier_shape, SH.property):
        path = shacl_graph.value(prop_shape, SH.path)
        if path == DATACITE.usesIdentifierScheme:
            assert (prop_shape, SH.minCount, Literal(1, datatype=XSD.integer)) in shacl_graph
            assert (prop_shape, SH.maxCount, Literal(1, datatype=XSD.integer)) in shacl_graph
            in_list = shacl_graph.value(prop_shape, SH['in'])
            assert in_list is not None
            items = list(Collection(shacl_graph, in_list))
            assert items == [DATACITE.doi, DATACITE.isbn, DATACITE.orcid]
            assert shacl_graph.value(prop_shape, SH.nodeKind) is None
            assert shacl_graph.value(prop_shape, SH.node) is None
