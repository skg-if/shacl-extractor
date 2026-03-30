# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelomas@gmail.com>
#
# SPDX-License-Identifier: ISC

import json
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

from src.main import _load_source, create_shacl_shapes

EXT_SRV_PATH = Path("ext-srv/data-model/ontology/current/srv.ttl")

pytestmark = pytest.mark.skipif(
    not EXT_SRV_PATH.exists(),
    reason="ext-srv submodule not available",
)


def _load_ext_srv_example(example_name: str) -> Graph:
    example_path = Path(f"ext-srv/examples/{example_name}")
    if not example_path.exists():
        pytest.skip("ext-srv examples not available")
    with open(example_path, 'r', encoding='utf-8') as f:
        jsonld_data = json.load(f)
    ext_ctx_path = Path("ext-srv/context/ver/current/skg-if.json")
    with open(ext_ctx_path, 'r', encoding='utf-8') as f:
        ext_ctx = json.load(f)["@context"]
    ext_ctx = {k: v for k, v in ext_ctx.items() if " " not in k}
    jsonld_data["@context"] = [
        "https://w3id.org/skg-if/context/1.1.0/skg-if.json",
        ext_ctx,
    ]
    data_graph = Graph()
    data_graph.parse(data=json.dumps(jsonld_data), format='json-ld')
    return data_graph


def test_ext_srv_module_name():
    modules, is_modular = _load_source(str(EXT_SRV_PATH))
    assert not is_modular
    assert list(modules.keys()) == ["srv"]


def test_ext_srv_langstring_generates_literal():
    shacl_graph = create_shacl_shapes(
        str(EXT_SRV_PATH),
        shapes_base="https://w3id.org/skg-if/shapes/srv/",
    )
    data_graph = _load_ext_srv_example("11234_1-1451.json")
    _, _, results_text = validate(
        data_graph=data_graph,
        shacl_graph=shacl_graph,
        debug=False,
    )
    assert "description" not in results_text
    SH = Namespace("http://www.w3.org/ns/shacl#")
    DCTERMS = Namespace("http://purl.org/dc/terms/")
    service_shape = URIRef("https://w3id.org/skg-if/shapes/srv/ServiceShape")
    desc_shapes = [
        ps for ps in shacl_graph.objects(service_shape, SH.property)
        if shacl_graph.value(ps, SH.path) == DCTERMS.description
    ]
    assert len(desc_shapes) == 1
    assert (desc_shapes[0], SH.nodeKind, SH.Literal) in shacl_graph


def test_ext_srv_shapes():
    shacl_graph = create_shacl_shapes(
        str(EXT_SRV_PATH),
        shapes_base="https://w3id.org/skg-if/shapes/srv/",
    )
    SH = Namespace("http://www.w3.org/ns/shacl#")
    shapes_base = "https://w3id.org/skg-if/shapes/srv/"
    standard_shape = URIRef(shapes_base + "StandardShape")
    assert (standard_shape, RDF.type, SH.NodeShape) in shacl_graph
    subject_term_shape = URIRef(shapes_base + "SubjectTermShape")
    assert (subject_term_shape, RDF.type, SH.NodeShape) in shacl_graph
    bibliometric_shape = URIRef(shapes_base + "BibliometricDataInTimeShape")
    assert (bibliometric_shape, RDF.type, SH.NodeShape) in shacl_graph
