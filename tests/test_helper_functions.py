# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelomas@gmail.com>
#
# SPDX-License-Identifier: ISC

from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

from src.main import (
    _derive_module_name,
    _derive_shapes_base,
    _detect_root_classes,
    _extract_prefixes_from_literals,
    _get_ext_module_name,
    _get_ontology_iri,
    _is_url,
    create_shacl_shapes,
)


def test_is_url():
    assert _is_url("https://example.org/ontology.ttl")
    assert _is_url("http://example.org/ontology.ttl")
    assert not _is_url("/path/to/file.ttl")
    assert not _is_url("relative/path.ttl")


def test_get_ontology_iri():
    g = Graph()
    g.parse(data='''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
<http://example.org/my-onto> a owl:Ontology .
''', format='turtle')
    assert _get_ontology_iri(g) == "http://example.org/my-onto"


def test_get_ontology_iri_missing():
    g = Graph()
    g.parse(data='''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix ex: <http://example.org/> .
ex:Thing a owl:Class .
''', format='turtle')
    assert _get_ontology_iri(g) is None


def test_get_ext_module_name():
    assert _get_ext_module_name("/path/to/ext-srv/data-model/ontology/current/srv.ttl") == "srv"
    assert _get_ext_module_name("/path/to/ext-foo/some/file.ttl") == "foo"
    assert _get_ext_module_name("/path/to/regular/ontology.ttl") is None


def test_derive_module_name_from_iri():
    g = Graph()
    g.parse(data='''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
<https://w3id.org/dharc/ontology/chad-ap> a owl:Ontology .
''', format='turtle')
    assert _derive_module_name("irrelevant", g) == "chad-ap"


def test_derive_module_name_from_file():
    g = Graph()
    g.parse(data='@prefix owl: <http://www.w3.org/2002/07/owl#> .', format='turtle')
    assert _derive_module_name("/path/to/my-ontology.ttl", g) == "my-ontology"


def test_derive_module_name_from_url():
    g = Graph()
    g.parse(data='@prefix owl: <http://www.w3.org/2002/07/owl#> .', format='turtle')
    assert _derive_module_name("https://example.org/path/onto.ttl", g) == "onto"


def test_derive_shapes_base_from_iri():
    g = Graph()
    g.parse(data='''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
<https://w3id.org/dharc/ontology/chad-ap> a owl:Ontology .
''', format='turtle')
    assert _derive_shapes_base("irrelevant", g) == "https://w3id.org/dharc/ontology/chad-ap/shapes/"


def test_derive_shapes_base_fallback():
    g = Graph()
    g.parse(data='@prefix owl: <http://www.w3.org/2002/07/owl#> .', format='turtle')
    assert _derive_shapes_base("irrelevant", g) == "http://example.org/shapes/"


def test_detect_root_classes():
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
    assert roots == {"http://example.org/Parent", "http://example.org/Standalone"}


def test_extract_prefixes_from_literals():
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
    assert prefixes == {
        "crm": "http://www.cidoc-crm.org/cidoc-crm/",
        "lrmoo": "http://iflastandards.info/ns/lrm/lrmoo/",
    }


def test_literal_prefix_resolution_in_shapes(temp_dir):
    ttl_file = Path(temp_dir) / "literal-prefix.ttl"
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
    assert len(shapes) == 1

    prop_shapes = list(shacl_graph.objects(shapes[0], SH.property))
    assert len(prop_shapes) == 1
    path = shacl_graph.value(prop_shapes[0], SH.path)
    assert str(path) == "http://iflastandards.info/ns/lrm/lrmoo/R3_is_realized_in"


def test_union_range_generates_sh_or(temp_dir):
    ttl_file = Path(temp_dir) / "union-range.ttl"
    with open(ttl_file, 'w', encoding='utf-8') as f:
        f.write('''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix ex: <http://example.org/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<http://example.org/test> a owl:Ontology .

ex:Container a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:hasItem -[0..N]-> ex:Alpha
* ex:hasItem -[0..N]-> ex:Beta""" .

ex:Alpha a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:alphaName -[1]-> rdfs:Literal""" .

ex:Beta a owl:Class ;
    dc:description """The properties that can be used with this class are:

* ex:betaValue -[1]-> rdfs:Literal""" .
''')

    shacl_graph = create_shacl_shapes(str(ttl_file))

    SH = Namespace("http://www.w3.org/ns/shacl#")
    EX = Namespace("http://example.org/")
    shapes_base = "http://example.org/test/shapes/"

    container_shape = URIRef(shapes_base + "ContainerShape")
    alpha_shape = URIRef(shapes_base + "AlphaShape")
    beta_shape = URIRef(shapes_base + "BetaShape")

    prop_shapes = list(shacl_graph.objects(container_shape, SH.property))
    hasitem_shapes = [
        ps for ps in prop_shapes
        if shacl_graph.value(ps, SH.path) == EX.hasItem
    ]
    assert len(hasitem_shapes) == 1

    or_list = list(shacl_graph.objects(hasitem_shapes[0], SH['or']))
    assert len(or_list) == 1

    or_members = list(shacl_graph.items(or_list[0]))
    assert len(or_members) == 2

    node_values = set()
    for member in or_members:
        node_val = shacl_graph.value(member, SH.node)
        if node_val:
            node_values.add(node_val)
    assert node_values == {alpha_shape, beta_shape}

    data = Graph()
    data.parse(data='''
@prefix ex: <http://example.org/> .

ex:c1 a ex:Container ;
    ex:hasItem ex:a1 .

ex:a1 a ex:Alpha ;
    ex:alphaName "test" .
''', format='turtle')

    conforms, _, results_text = validate(
        data_graph=data,
        shacl_graph=shacl_graph,
        debug=False,
    )
    assert conforms, f"Union range validation failed:\n{results_text}"


def test_unqualified_target_name(temp_dir):
    ttl_file = Path(temp_dir) / "unqualified.ttl"
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
    assert len(activity_props) == 2

    for prop_shape in activity_props:
        path = shacl_graph.value(prop_shape, SH.path)
        if path == CRM.P32_used_general_technique:
            assert (prop_shape, SH.node, type_shape) in shacl_graph
