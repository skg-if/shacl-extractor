import argparse
import re
from pathlib import Path
from typing import Optional

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, XSD

SHAPES_BASE = "https://w3id.org/skg-if/shapes/"
DC_DESCRIPTION = URIRef("http://purl.org/dc/elements/1.1/description")

ROOT_CLASSES = {
    "agent": "http://xmlns.com/foaf/0.1/Agent",
    "data-source": "http://www.w3.org/ns/dcat#DataService",
    "grant": "http://purl.org/cerif/frapo/Grant",
    "research-product": "http://purl.org/spar/fabio/Work",
    "topic": "http://purl.org/spar/fabio/SubjectTerm",
    "venue": "http://purl.org/spar/fabio/ExpressionCollection",
}


def get_ontology_path(version: Optional[str] = None) -> str:
    """
    Get the path to the ontology directory based on version.
    If version is None, returns the current version.
    Only supports modular ontology structure (1.0.1+).
    """
    base_path = Path("data-model/ontology")

    if version is None:
        version = "current"

    version_path = base_path / version

    if not version_path.exists():
        raise ValueError(f"Ontology version {version} not found at {version_path}")

    if not version_path.is_dir():
        raise ValueError(f"Single-file ontologies are not supported. Use version 1.0.1 or later: {version_path}")

    return str(version_path)


def load_ontology(path: str) -> Graph:
    """
    Load the ontology from the given path (legacy function for compatibility).
    For 1.0.1+ versions, combines all module TTL files.
    For earlier versions, loads the single TTL file.
    """
    g = Graph()
    path = Path(path)

    if path.is_file():
        g.parse(path, format='turtle', encoding='utf-8')
    else:
        module_dirs = [d for d in path.iterdir() if d.is_dir() and d.name != "resources"]
        for module_dir in module_dirs:
            ttl_files = list(module_dir.glob("*.ttl"))
            if ttl_files:
                g.parse(ttl_files[0], format='turtle', encoding='utf-8')

    return g


def load_ontology_by_module(path: str) -> dict[str, Graph]:
    """
    Load the ontology returning separate graphs per module.
    Returns {module_name: Graph}.
    Only supports modular ontology structure (1.0.1+).
    """
    modules = {}
    path = Path(path)

    if path.is_file():
        raise ValueError(f"Single-file ontologies are not supported. Use a modular ontology directory: {path}")

    module_dirs = [d for d in path.iterdir() if d.is_dir() and d.name != "resources"]
    for module_dir in sorted(module_dirs):
        ttl_files = list(module_dir.glob("*.ttl"))
        if ttl_files:
            g = Graph()
            g.parse(ttl_files[0], format='turtle', encoding='utf-8')
            modules[module_dir.name] = g

    return modules


def get_class_local_name(class_uri: str) -> str:
    """Extract local name from a class URI."""
    if '#' in class_uri:
        return class_uri.split('#')[-1]
    return class_uri.split('/')[-1]


def create_shacl_shapes(input_file: str) -> Graph:
    """
    Create SHACL shapes from ontology modules.
    Each module gets its own namespace for shapes.
    """
    modules = load_ontology_by_module(input_file)

    shacl = Graph()
    SH = Namespace("http://www.w3.org/ns/shacl#")
    shacl.bind('sh', SH)

    for module_name, g in modules.items():
        for prefix, namespace in g.namespaces():
            shacl.bind(prefix, namespace)


    class_to_modules = {}
    for module_name, g in modules.items():
        for cls in g.subjects(RDF.type, OWL.Class, unique=True):
            desc = g.value(cls, DC_DESCRIPTION)
            if desc and "The properties that can be used" in str(desc):
                class_uri = str(cls)
                if class_uri not in class_to_modules:
                    class_to_modules[class_uri] = []
                class_to_modules[class_uri].append(module_name)

    for module_name in modules.keys():
        shape_ns = SHAPES_BASE + module_name + "/"
        prefix = f"skg-sh-{module_name}".replace("-", "_")
        shacl.bind(prefix, Namespace(shape_ns))

    for module_name, g in modules.items():
        shape_ns = Namespace(SHAPES_BASE + module_name + "/")
        root_class = ROOT_CLASSES[module_name]

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

            if class_uri == root_class:
                shacl.add((shape_uri, SH.targetClass, cls))

            # Skip first element (header text before first property)
            properties = [p for p in re.split(r'\n[*-] ', desc_str) if p.strip()][1:]

            for prop in properties:
                prop_text = prop.strip()
                match = re.match(r'([\w:]+) -\[(\d+|[*N])(\.\.)?(\d+|[*N])?]->\s+([\w:]+)', prop_text)
                if not match:
                    raise ValueError(f"Invalid property format in {class_uri}: {prop_text}")

                prop_name, card_min, range_sep, card_max, target = match.groups()

                prop_prefix, prop_local = prop_name.split(':')
                prop_ns = g.store.namespace(prop_prefix)
                if not prop_ns:
                    raise ValueError(f"Unknown prefix '{prop_prefix}' in {class_uri}: {prop_text}")

                prop_uri = URIRef(str(prop_ns) + prop_local)

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

                target_prefix, target_local = target.split(':')
                target_ns = g.store.namespace(target_prefix)
                if not target_ns:
                    raise ValueError(f"Unknown prefix '{target_prefix}' in {class_uri}: {prop_text}")

                if target == "rdfs:Literal":
                    shacl.add((bnode, SH.nodeKind, SH.Literal))
                elif target.startswith("xsd:"):
                    shacl.add((bnode, SH.datatype, URIRef(f"http://www.w3.org/2001/XMLSchema#{target_local}")))
                else:
                    target_uri = URIRef(str(target_ns) + target_local)
                    target_class_uri = str(target_uri)

                    if target_class_uri in class_to_modules:
                        target_modules = class_to_modules[target_class_uri]
                        if module_name in target_modules:
                            target_module = module_name
                        else:
                            target_module = sorted(target_modules)[0]

                        target_shape_ns = SHAPES_BASE + target_module + "/"
                        target_shape_uri = URIRef(target_shape_ns + target_local + "Shape")
                        shacl.add((bnode, SH.node, target_shape_uri))
                    else:
                        shacl.add((bnode, SH.nodeKind, SH.BlankNodeOrIRI))

    return shacl


def main():
    parser = argparse.ArgumentParser(description='Convert SKG ontology to SHACL shapes')
    parser.add_argument('--input', help='Input TTL file path (optional)')
    parser.add_argument('--version', help='Ontology version (e.g., "1.0.0", "current")')
    parser.add_argument('output', help='Output SHACL file path')

    args = parser.parse_args()

    try:
        if args.input:
            input_path = args.input
        else:
            input_path = get_ontology_path(args.version)
    except ValueError as e:
        parser.error(str(e))
        return

    shacl_graph = create_shacl_shapes(input_path)
    shacl_graph.serialize(destination=args.output, format="turtle", encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    main()
