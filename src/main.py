import argparse
import re
from pathlib import Path
from typing import Optional

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, XSD

def get_ontology_path(version: Optional[str] = None) -> str:
    """
    Get the path to the ontology file based on version.
    If version is None, returns the current version.
    """
    base_path = Path("data-model/ontology")
    
    if version is None:
        version = "current"
        
    version_path = base_path / version
    
    # For versions 1.0.1 and later, we need to combine module files
    if version == "1.0.1" or version == "current":
        return str(version_path)
    else:
        # For earlier versions, use the single TTL file
        ttl_path = version_path / "skg-o.ttl"
        if not ttl_path.exists():
            raise ValueError(f"Ontology version {version} not found at {ttl_path}")
        return str(ttl_path)

def load_ontology(path: str) -> Graph:
    """
    Load the ontology from the given path.
    For 1.0.1+ versions, combines all module TTL files.
    For earlier versions, loads the single TTL file.
    """
    g = Graph()
    path = Path(path)
    
    if path.is_file():
        # Pre-1.0.1: Single TTL file
        g.parse(path, format='turtle', encoding='utf-8')
    else:
        # 1.0.1+: Multiple module files
        module_dirs = [d for d in path.iterdir() if d.is_dir() and not d.name == "resources"]
        
        for module_dir in module_dirs:
            ttl_files = list(module_dir.glob("*.ttl"))
            if ttl_files:
                g.parse(ttl_files[0], format='turtle', encoding='utf-8')
                
    return g

def create_shacl_shapes(input_file: str) -> Graph:
    g = load_ontology(input_file)
    
    shacl = Graph()
    SH = Namespace("http://www.w3.org/ns/shacl#")
    shacl.bind('sh', SH)
    
    for prefix, namespace in g.namespaces():
        shacl.bind(prefix, namespace)
    
    for cls in g.subjects(RDF.type, OWL.Class, unique=True):
        desc = g.value(cls, URIRef("http://purl.org/dc/elements/1.1/description"))
        if desc:
            shape_uri = URIRef(str(cls) + 'Shape')
            shacl.add((shape_uri, RDF.type, SH.NodeShape))
            shacl.add((shape_uri, SH.targetClass, cls))
            
            desc_str = str(desc)
            # Split on either '* ' or '- ' at the start of lines
            properties = [p for p in re.split(r'\n[*-] ', desc_str) if p.strip()]
            
            for prop in properties:
                if not prop.strip():
                    continue
                
                match = re.match(r'([\w:]+) -\[(\d+|[*N])(\.\.)?(\d+|[*N])?]->\s+([\w:]+)', prop.strip())
                if match:
                    prop_name, card_min, range_sep, card_max, target = match.groups()
                    
                    prefix, local = prop_name.split(':')
                    ns = str(g.store.namespace(prefix))
                    if ns:
                        prop_uri = URIRef(ns + local)
                        
                        # Create property shape
                        bnode = BNode()
                        shacl.add((shape_uri, SH.property, bnode))
                        shacl.add((bnode, SH.path, prop_uri))
                        
                        # Handle cardinality
                        if range_sep is None and card_min not in ['*', 'N']:
                            exact_card = int(card_min)
                            shacl.add((bnode, SH.minCount, Literal(exact_card, datatype=XSD.integer)))
                            shacl.add((bnode, SH.maxCount, Literal(exact_card, datatype=XSD.integer)))
                        else:
                            if card_min and card_min not in ['*', 'N']:
                                shacl.add((bnode, SH.minCount, Literal(int(card_min), datatype=XSD.integer)))
                            if card_max and card_max not in ['*', 'N']:
                                shacl.add((bnode, SH.maxCount, Literal(int(card_max), datatype=XSD.integer)))
                        
                        # Handle target type
                        if target:
                            target_prefix, target_local = target.split(':')
                            target_ns = str(g.store.namespace(target_prefix))
                            if target_ns:
                                if target == "rdfs:Literal":
                                    shacl.add((bnode, SH.nodeKind, SH.Literal))
                                elif target.startswith("xsd:"):
                                    shacl.add((bnode, SH.datatype, URIRef(f"http://www.w3.org/2001/XMLSchema#{target_local}")))
                                else:
                                    # Create an or between class and nodeKind
                                    or_node = BNode()
                                    shacl.add((bnode, SH['or'], or_node))
                                    
                                    # First alternative: the specific class
                                    class_constraint = BNode()
                                    shacl.add((or_node, RDF.first, class_constraint))
                                    shacl.add((class_constraint, SH['class'], URIRef(target_ns + target_local)))
                                    
                                    # Second alternative: any IRI or blank node
                                    rest_node = BNode()
                                    shacl.add((or_node, RDF.rest, rest_node))
                                    
                                    nodekind_constraint = BNode()
                                    shacl.add((rest_node, RDF.first, nodekind_constraint))
                                    shacl.add((nodekind_constraint, SH.nodeKind, SH.BlankNodeOrIRI))
                                    shacl.add((rest_node, RDF.rest, RDF.nil))
    
    return shacl

def main():
    parser = argparse.ArgumentParser(description='Convert SKG ontology to SHACL shapes')
    parser.add_argument('--input', help='Input TTL file path (optional)')
    parser.add_argument('--version', help='Ontology version (e.g., "1.0.0", "current")')
    parser.add_argument('output', help='Output SHACL file path')
    
    args = parser.parse_args()
    
    # If no input file is specified, use the versioned ontology
    if args.input:
        input_path = args.input
    else:
        try:
            input_path = get_ontology_path(args.version)
        except ValueError as e:
            parser.error(str(e))
    
    shacl_graph = create_shacl_shapes(input_path)
    shacl_graph.serialize(destination=args.output, format="turtle", encoding="utf-8")

if __name__ == "__main__": # pragma: no cover
    main()