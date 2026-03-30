# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelomas@gmail.com>
#
# SPDX-License-Identifier: ISC

import json
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

from src.main import SHAPES_BASE, create_shacl_shapes

SKGIF_PATH = Path("data-model/ontology/current")

pytestmark = pytest.mark.skipif(
    not SKGIF_PATH.exists(),
    reason="SKG-IF submodules not available",
)


def test_current_ontology_conversion(temp_dir):
    output_file = Path(temp_dir) / "current_ontology_shapes.ttl"

    shacl_graph = create_shacl_shapes(str(SKGIF_PATH))
    shacl_graph.serialize(destination=output_file, format="turtle", encoding="utf-8")

    SH = Namespace("http://www.w3.org/ns/shacl#")
    FRAPO = Namespace("http://purl.org/cerif/frapo/")
    FOAF = Namespace("http://xmlns.com/foaf/0.1/")
    PRISM = Namespace("http://prismstandard.org/namespaces/basic/2.0/")
    XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

    grant_shape = URIRef(SHAPES_BASE + "grant/GrantShape")
    assert (grant_shape, RDF.type, SH.NodeShape) in shacl_graph

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
                assert (prop_shape, SH.datatype, expected_properties[prop_name]['datatype']) in shacl_graph
            if 'nodeKind' in expected_properties[prop_name]:
                assert (prop_shape, SH.nodeKind, expected_properties[prop_name]['nodeKind']) in shacl_graph

    assert found_properties == set(expected_properties.keys())

    agent_shape = URIRef(SHAPES_BASE + "agent/AgentShape")
    assert (agent_shape, RDF.type, SH.NodeShape) in shacl_graph

    agent_properties = list(shacl_graph.objects(agent_shape, SH.property))

    name_found = False
    for prop_shape in agent_properties:
        path = shacl_graph.value(prop_shape, SH.path)
        if path == FOAF.name:
            name_found = True
            assert (prop_shape, SH.nodeKind, SH.Literal) in shacl_graph

    assert name_found


def test_opencitations_example_validation():
    examples_path = Path('examples/OpenCitations/oc_1.jsonld')
    if not examples_path.exists():
        pytest.skip("OpenCitations examples not available")

    shapes_graph = create_shacl_shapes(str(SKGIF_PATH))

    data_graph = Graph()
    with open(examples_path, 'r', encoding='utf-8') as f:
        jsonld_data = json.load(f)

    data_graph.parse(data=json.dumps(jsonld_data), format='json-ld')

    conforms, results_graph, results_text = validate(
        data_graph=data_graph,
        shacl_graph=shapes_graph,
        debug=False,
    )

    assert conforms, (
        f"OpenCitations example data does not conform to SHACL shapes. "
        f"Validation results:\n{results_text}"
    )


def test_all_current_examples_validation():
    examples_path = Path('context/ver/current/samples')
    if not examples_path.exists():
        pytest.skip("Context submodule not available")

    shapes_graph = create_shacl_shapes(str(SKGIF_PATH))
    example_files = list(examples_path.glob('example-*.json'))

    for example_file in example_files:
        data_graph = Graph()
        with open(example_file, 'r', encoding='utf-8') as f:
            jsonld_data = json.load(f)

        data_graph.parse(data=json.dumps(jsonld_data), format='json-ld')

        conforms, results_graph, results_text = validate(
            data_graph=data_graph,
            shacl_graph=shapes_graph,
            debug=False,
        )

        assert conforms, (
            f"{example_file.name} does not conform to SHACL shapes. "
            f"Validation results:\n{results_text}"
        )
