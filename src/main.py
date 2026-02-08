import argparse
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, XSD

SHAPES_BASE = "https://w3id.org/skg-if/shapes/"
DC_DESCRIPTION = URIRef("http://purl.org/dc/elements/1.1/description")
PROPERTY_PATTERN = r'([\w:-]+) -\[(\d+|[*N])(\.\.)?(\d+|[*N])?]->\s+([\w:-]+)'

ROOT_CLASSES = {
    "agent": "http://xmlns.com/foaf/0.1/Agent",
    "data-source": "http://www.w3.org/ns/dcat#DataService",
    "grant": "http://purl.org/cerif/frapo/Grant",
    "research-product": "http://purl.org/spar/fabio/Work",
    "topic": "http://purl.org/spar/fabio/SubjectTerm",
    "venue": "http://purl.org/spar/fabio/ExpressionCollection",
}


def _is_url(source: str) -> bool:
    return source.startswith('http://') or source.startswith('https://')


def _get_ontology_iri(g: Graph) -> Optional[str]:
    for s in g.subjects(RDF.type, OWL.Ontology, unique=True):
        return str(s)
    return None


def _derive_module_name(source: str, g: Graph) -> str:
    iri = _get_ontology_iri(g)
    if iri:
        parsed = urlparse(iri)
        parts = [p for p in parsed.path.rstrip('/').split('/') if p]
        if parts:
            return parts[-1]
    if _is_url(source):
        parsed = urlparse(source)
        parts = [p for p in parsed.path.rstrip('/').split('/') if p]
    else:
        parts = [Path(source).stem]
    if parts:
        name = parts[-1]
        if '.' in name:
            name = name.rsplit('.', 1)[0]
        return name
    return "ontology"


def _derive_shapes_base(source: str, g: Graph) -> str:
    iri = _get_ontology_iri(g)
    if iri:
        return iri.rstrip('/') + '/shapes/'
    return "http://example.org/shapes/"


PREFIX_PATTERN = re.compile(r'@prefix\s+(\w+):\s+<([^>]+)>\s*\.')


def _build_uri_namespace_map(g: Graph) -> dict[str, str]:
    result: dict[str, str] = {}
    for s, p, o in g:
        for term in (s, p, o):
            if not isinstance(term, URIRef):
                continue
            uri = str(term)
            if '#' in uri:
                idx = uri.rindex('#') + 1
            elif '/' in uri:
                idx = uri.rindex('/') + 1
            else:
                continue
            local = uri[idx:]
            ns = uri[:idx]
            if local and ns:
                result[local] = ns
    return result


def _extract_prefixes_from_literals(g: Graph) -> dict[str, str]:
    result: dict[str, str] = {}
    for _, _, o in g:
        if not isinstance(o, Literal):
            continue
        for match in PREFIX_PATTERN.finditer(str(o)):
            result[match.group(1)] = match.group(2)
    return result


def _resolve_namespace(prefix: str, local_name: str, g: Graph,
                       uri_ns_map: dict[str, str],
                       literal_prefix_map: dict[str, str]) -> Optional[str]:
    ns = g.store.namespace(prefix)
    if ns:
        return str(ns)
    if local_name in uri_ns_map:
        return uri_ns_map[local_name]
    if prefix in literal_prefix_map:
        return literal_prefix_map[prefix]
    return None


def _detect_root_classes(g: Graph, described_classes: set[str]) -> set[str]:
    uri_ns_map = _build_uri_namespace_map(g)
    literal_prefix_map = _extract_prefixes_from_literals(g)
    referenced = set()
    for cls in g.subjects(RDF.type, OWL.Class, unique=True):
        desc = g.value(cls, DC_DESCRIPTION)
        if not desc or "The properties that can be used" not in str(desc):
            continue
        properties = [p for p in re.split(r'\n[*-] ', str(desc)) if p.strip()][1:]
        for prop in properties:
            match = re.match(PROPERTY_PATTERN, prop.strip())
            if not match:
                continue
            target = match.group(5)
            if ':' in target:
                target_prefix, target_local = target.split(':')
                if target_prefix in ('rdfs', 'xsd'):
                    continue
                target_ns = _resolve_namespace(target_prefix, target_local, g, uri_ns_map, literal_prefix_map)
            else:
                target_local = target
                target_ns = uri_ns_map.get(target)
            if target_ns:
                referenced.add(target_ns + target_local)
    return described_classes - referenced


def load_ontology_by_module(path: str) -> dict[str, Graph]:
    modules = {}
    path_obj = Path(path)

    module_dirs = [d for d in path_obj.iterdir() if d.is_dir() and d.name != "resources"]
    for module_dir in sorted(module_dirs):
        rdf_files = list(module_dir.glob("*.ttl")) + list(module_dir.glob("*.rdf")) + list(module_dir.glob("*.owl")) + list(module_dir.glob("*.n3")) + list(module_dir.glob("*.nt")) + list(module_dir.glob("*.jsonld"))
        if rdf_files:
            g = Graph()
            g.parse(rdf_files[0])
            modules[module_dir.name] = g

    return modules


def get_class_local_name(class_uri: str) -> str:
    if '#' in class_uri:
        return class_uri.split('#')[-1]
    return class_uri.split('/')[-1]


def _load_source(input_source: str) -> tuple[dict[str, Graph], bool]:
    if _is_url(input_source):
        g = Graph()
        g.parse(input_source)
        module_name = _derive_module_name(input_source, g)
        return {module_name: g}, False

    path = Path(input_source)
    if path.is_dir():
        return load_ontology_by_module(input_source), True

    g = Graph()
    g.parse(input_source)
    module_name = _derive_module_name(input_source, g)
    return {module_name: g}, False


def _resolve_shapes_base(input_source: str, modules: dict[str, Graph], is_modular: bool, shapes_base: Optional[str]) -> str:
    if shapes_base:
        return shapes_base
    if is_modular:
        return SHAPES_BASE
    first_g = next(iter(modules.values()))
    return _derive_shapes_base(input_source, first_g)


def _build_class_to_modules(modules: dict[str, Graph]) -> dict[str, list[str]]:
    class_to_modules: dict[str, list[str]] = {}
    for module_name, g in modules.items():
        for cls in g.subjects(RDF.type, OWL.Class, unique=True):
            desc = g.value(cls, DC_DESCRIPTION)
            if desc and "The properties that can be used" in str(desc):
                class_uri = str(cls)
                if class_uri not in class_to_modules:
                    class_to_modules[class_uri] = []
                class_to_modules[class_uri].append(module_name)
    return class_to_modules


def _resolve_root_class_uris(modules: dict[str, Graph], class_to_modules: dict[str, list[str]], is_modular: bool) -> set[str]:
    if is_modular:
        return set(ROOT_CLASSES.values())
    all_graphs = Graph()
    for g in modules.values():
        for triple in g:
            all_graphs.add(triple)
    for g in modules.values():
        for prefix, namespace in g.namespaces():
            all_graphs.bind(prefix, namespace)
    return _detect_root_classes(all_graphs, set(class_to_modules.keys()))


def _bind_namespaces(shacl: Graph, modules: dict[str, Graph]) -> None:
    for _, g in modules.items():
        for prefix, namespace in g.namespaces():
            shacl.bind(prefix, namespace)


def _bind_shape_namespaces(shacl: Graph, modules: dict[str, Graph], shapes_base: str, is_modular: bool) -> None:
    if is_modular:
        for module_name in modules.keys():
            shape_ns = shapes_base + module_name + "/"
            prefix = f"skg-sh-{module_name}".replace("-", "_")
            shacl.bind(prefix, Namespace(shape_ns))
    else:
        module_name = next(iter(modules.keys()))
        prefix = module_name.replace("-", "_") + "_sh"
        shacl.bind(prefix, Namespace(shapes_base))


def _process_property(prop_text: str, class_uri: str, g: Graph, shape_uri: URIRef,
                      class_to_modules: dict[str, list[str]], module_name: str,
                      shapes_base: str, is_modular: bool, shacl: Graph, SH: Namespace,
                      uri_ns_map: dict[str, str],
                      literal_prefix_map: dict[str, str]) -> None:
    match = re.match(PROPERTY_PATTERN, prop_text)
    if not match:
        raise ValueError(f"Invalid property format in {class_uri}: {prop_text}")

    prop_name, card_min, range_sep, card_max, target = match.groups()

    prop_prefix, prop_local = prop_name.split(':')
    prop_ns = _resolve_namespace(prop_prefix, prop_local, g, uri_ns_map, literal_prefix_map)
    if not prop_ns:
        raise ValueError(f"Unknown prefix '{prop_prefix}' in {class_uri}: {prop_text}")

    prop_uri = URIRef(prop_ns + prop_local)

    bnode = BNode()
    shacl.add((shape_uri, SH.property, bnode))
    shacl.add((bnode, SH.path, prop_uri))

    if range_sep is None and card_min not in ['*', 'N']:
        exact_card = int(card_min)
        shacl.add((bnode, SH.minCount, Literal(exact_card, datatype=XSD.integer)))
        shacl.add((bnode, SH.maxCount, Literal(exact_card, datatype=XSD.integer)))
    else:
        if card_min and card_min not in ['*', 'N']:
            shacl.add((bnode, SH.minCount, Literal(int(card_min), datatype=XSD.integer)))
        if card_max and card_max not in ['*', 'N']:
            shacl.add((bnode, SH.maxCount, Literal(int(card_max), datatype=XSD.integer)))

    if ':' in target:
        target_prefix, target_local = target.split(':')
        target_ns = _resolve_namespace(target_prefix, target_local, g, uri_ns_map, literal_prefix_map)
        if not target_ns:
            raise ValueError(f"Unknown prefix '{target_prefix}' in {class_uri}: {prop_text}")
    else:
        target_local = target
        target_ns = uri_ns_map.get(target)
        if not target_ns:
            raise ValueError(f"Cannot resolve unqualified name '{target}' in {class_uri}: {prop_text}")

    if target == "rdfs:Literal":
        shacl.add((bnode, SH.nodeKind, SH.Literal))
    elif target.startswith("xsd:"):
        shacl.add((bnode, SH.datatype, URIRef(f"http://www.w3.org/2001/XMLSchema#{target_local}")))
    else:
        target_uri = URIRef(target_ns + target_local)
        target_class_uri = str(target_uri)

        if target_class_uri in class_to_modules:
            target_modules = class_to_modules[target_class_uri]
            if module_name in target_modules:
                target_module = module_name
            else:
                target_module = sorted(target_modules)[0]

            target_shape_ns = shapes_base + target_module + "/" if is_modular else shapes_base
            target_shape_uri = URIRef(target_shape_ns + target_local + "Shape")
            shacl.add((bnode, SH.node, target_shape_uri))
        else:
            shacl.add((bnode, SH.nodeKind, SH.BlankNodeOrIRI))


def create_shacl_shapes(input_source: str | Path, shapes_base: Optional[str] = None) -> Graph:
    input_source = str(input_source)
    modules, is_modular = _load_source(input_source)
    shapes_base = _resolve_shapes_base(input_source, modules, is_modular, shapes_base)

    shacl = Graph()
    SH = Namespace("http://www.w3.org/ns/shacl#")
    shacl.bind('sh', SH)

    _bind_namespaces(shacl, modules)

    class_to_modules = _build_class_to_modules(modules)
    root_class_uris = _resolve_root_class_uris(modules, class_to_modules, is_modular)

    _bind_shape_namespaces(shacl, modules, shapes_base, is_modular)

    for module_name, g in modules.items():
        shape_ns = Namespace(shapes_base + module_name + "/") if is_modular else Namespace(shapes_base)
        uri_ns_map = _build_uri_namespace_map(g)
        literal_prefix_map = _extract_prefixes_from_literals(g)

        for cls in g.subjects(RDF.type, OWL.Class, unique=True):
            desc = g.value(cls, DC_DESCRIPTION)
            if not desc:
                continue

            desc_str = str(desc)
            if "The properties that can be used" not in desc_str:
                continue

            class_uri = str(cls)
            class_local = get_class_local_name(class_uri)
            shape_uri = URIRef(str(shape_ns) + class_local + "Shape")

            shacl.add((shape_uri, RDF.type, SH.NodeShape))

            if class_uri in root_class_uris:
                shacl.add((shape_uri, SH.targetClass, cls))

            properties = [p for p in re.split(r'\n[*-] ', desc_str) if p.strip()][1:]

            for prop in properties:
                prop_text = prop.strip()
                _process_property(prop_text, class_uri, g, shape_uri,
                                  class_to_modules, module_name,
                                  shapes_base, is_modular, shacl, SH,
                                  uri_ns_map, literal_prefix_map)

    return shacl


def main():
    parser = argparse.ArgumentParser(description='Extract SHACL shapes from OWL ontologies')
    parser.add_argument('input', help='Input ontology (file path, directory, or URL)')
    parser.add_argument('output', help='Output SHACL file path')
    parser.add_argument('--shapes-base', help='Base URL for shapes namespace')

    args = parser.parse_args()

    shacl_graph = create_shacl_shapes(args.input, shapes_base=args.shapes_base)
    shacl_graph.serialize(destination=args.output, format="turtle", encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    main()
