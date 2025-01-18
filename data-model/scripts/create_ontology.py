from glob import glob
from os.path import sep, exists, splitext, basename, dirname
from os import makedirs
from argparse import ArgumentParser
from re import findall, sub, search 
from pprint import pprint
from collections import defaultdict
from bs4 import BeautifulSoup
from datetime import datetime
from rdflib import Graph, OWL, RDF, RDFS, URIRef, Literal, DC, VANN, XSD
import logging


# Formats available
formats = {
    "json-ld": "json",
    "xml": "xml",
    "turtle": "ttl",
    "nt11": "nt"
}

# Prefixes of ontological entities
prefixes = {
    "bido": "http://purl.org/spar/bido/",
    "cito": "http://purl.org/spar/cito/",
    "co": "http://purl.org/co/",
    "coar": "http://purl.org/coar/access_right/",
    "datacite": "http://purl.org/spar/datacite/",
    "dcat": "http://www.w3.org/ns/dcat#",
    "dcterms": "http://purl.org/dc/terms/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "fabio": "http://purl.org/spar/fabio/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "frapo": "http://purl.org/cerif/frapo/",
    "frbr": "http://purl.org/vocab/frbr/core#",
    "lcc": "http://id.loc.gov/authorities/classification/",
    "loc": "http://id.loc.gov/authorities/",
    "literal": "http://www.essepuntato.it/2010/06/literalreification/",
    "odrl": "http://www.w3.org/ns/odrl/2/",
    "org": "https://www.w3.org/ns/org#",
    "prism": "http://prismstandard.org/namespaces/basic/2.0/",
    "pro": "http://purl.org/spar/pro/",
    "pso": "http://purl.org/spar/pso/",
    "prov": "http://www.w3.org/ns/prov#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "schema": "https://schema.org/",
    "scoro": "http://purl.org/spar/scoro/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "ti": "http://www.ontologydesignpatterns.org/cp/owl/timeinterval.owl#",
    "tvc": "http://www.essepuntato.it/2012/04/tvc/",
    "vivo": "http://vivoweb.org/ontology/core#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "vann": "http://purl.org/vocab/vann/",
    "owl": str(OWL)
}


def normalise(s):
    s = sub("\s+", " ", s).strip()
    return s

def clean_term(s):
    s = normalise(s)

    to_remove = {"`"}
    for c in to_remove:
        s = s.replace(c, "")

    return s


def clean_definition(s):
    s = normalise(s)

    to_split = {"]("}
    for c in to_split:
        s = s.replace(c, " ".join(list(c)))

    to_remove = {"[", "]", "**", "<", ">"}
    for c in to_remove:
        s = s.replace(c, "")

    return s

def gather_entities_and_labels(soup, consider_edges, d_support, file_name):
    terms = set()

    entity_type = "node"
    entity_label = "y:NodeLabel"
    if consider_edges:
        entity_type = "edge"
        entity_label = "y:EdgeLabel"

    for element in soup.find_all(entity_type):
        element_id = file_name + "#" + element["id"]

        if consider_edges:
            element_source = file_name + "#" + element["source"]
            element_target = file_name + "#" + element["target"]
            d_support["domain_range"][element_id]["domain"] = element_source
            d_support["domain_range"][element_id]["range"] = element_target

        element_label = normalise("".join(element.find(entity_label, recursive=True).strings))
        element_label_sequence = findall("(\w+:[\w-]+)( \(([ \w-]+)\))?", element_label)
        for entity, _, label in element_label_sequence:
            terms.add(entity)
            
            if label != "":
                d_support["term_mapping"][entity].add(label)
        
            d_support["entity_id"][entity].add(element_id)
            d_support["id_entity"][element_id].add(entity)
    
    return terms


def extract_datatypes(entity_set, datatype_prefixes, datatype_set):
    for entity in entity_set:
        entity_prefix = sub("([^:]+):.+", "\\1", entity)
        if entity_prefix in datatype_prefixes:
            datatype_set.add(entity)
    
    entity_set.difference_update(datatype_set)


def get_full_url(entity_name, prefixes):
    prefix = sub("([^:]+):.+", "\\1", entity_name)
    return entity_name.replace(prefix + ":", prefixes[prefix])


def get_prefix_url(entity_name, prefixes):
    prefix = sub("([^:]+):.+", "\\1", entity_name)
    return prefixes[prefix]


def not_basic_ontology_entity(entity_string):
    return not entity_string.startswith("owl:") and not entity_string.startswith("rdf:") and not entity_string.startswith("rdfs:")


def create_entity(entity, entity_type, prefixes, ontology, d_support):
    if not_basic_ontology_entity(entity):
        entity_iri = URIRef(get_full_url(entity, prefixes))
        ontology.add((entity_iri, RDF.type, entity_type))

        additional_label = ""
        if entity in d_support["term_mapping"]:
            additional_label = " (SKG-IF labels: " + ", ".join(d_support["term_mapping"][entity]) + ")" 
        ontology.add((entity_iri, RDFS.label, Literal(entity + additional_label)))

        ontology.add((entity_iri, RDFS.isDefinedBy, URIRef(get_prefix_url(entity, prefixes))))

        for entity_label in d_support["term_mapping"][entity]:
            if entity_label in d_support["definitions"]:
                ontology.add((entity_iri, RDFS.comment, 
                              Literal(d_support["definitions"][entity_label])))
                break

        return entity_iri


def get_domain_range_entity_names(property, is_domain, d_support):
    result = set()

    rel_type = "range"
    if is_domain:
        rel_type = "domain"

    property_ids = d_support["entity_id"][property]
    for property_id in property_ids:
        property_range_id = d_support["domain_range"][property_id][rel_type]
        result.update(d_support["id_entity"][property_range_id])
    
    return sorted(list(result))


def get_domain_properties(class_name, d_support):
    class_ids = d_support["entity_id"][class_name]

    selected_properties = list()
    for property_id, d_r in d_support["domain_range"].items():
        if d_r["domain"] in class_ids:
            for property in d_support["id_entity"][property_id]:
                for target_class in d_support["id_entity"][d_r["range"]]:
                    item = (property, target_class)
                    if item not in selected_properties:
                        selected_properties.append(item)
    
    return sorted(selected_properties)


def create_domain_range(property, property_iri, ontology, d_support, is_object_property):
    domain_entities = get_domain_range_entity_names(property, True, d_support)
    range_entities = get_domain_range_entity_names(property, False, d_support)

    domain_strings = ["In SKG-IF, it is used in the following classes (domain):"]
    for entity in domain_entities:
        domain_strings.append("* " + entity)
    
    range_type = "data types"
    if is_object_property:
        range_type = "classes"

    range_strings = ["In SKG-IF, it is used to link to entities belonging to the following " + range_type + " (range):"]
    for entity in range_entities:
        range_strings.append("* " + entity)
    
    ontology.add((property_iri, DC.description, 
                  Literal("\n".join(domain_strings) + "\n\n" + "\n".join(range_strings))))

def associate_definitions(level_defs, file_string, d_support):
    for level_dev_regex, extract_regex in level_defs:
        level_dev = findall(level_dev_regex, file_string)
        for key, definition in level_dev:
            value = clean_definition(definition)
            if extract_regex is not None:
                value = sub(extract_regex, "\\1", value)
            d_support["definitions"][clean_term(key)] = value

def create_ontology(classes, object_properties, data_properties, individuals, prefixes, d_support, version=None):
    onto = Graph()

    for prefix, base_url in prefixes.items():
        onto.bind(prefix, base_url)

    onto.add((DC.description, RDF.type, OWL.AnnotationProperty))
    onto.add((DC.date, RDF.type, OWL.AnnotationProperty))
    onto.add((DC.title, RDF.type, OWL.AnnotationProperty))

    onto_iri = URIRef("https://w3id.org/skg-if/ontology/")
    onto.add((onto_iri, RDF.type, OWL.Ontology))
    onto.add((onto_iri, RDFS.label, Literal("SKG-O")))
    onto.add((onto_iri, DC.title, Literal("The SKG-IF Ontology")))
    onto.add((onto_iri, RDFS.comment, Literal("SKG-O, the SKG-IF Ontology, is not yet another bibliographic ontology. Rather it is just a place where existing and complementary ontological entities from several other ontologies, all employed in the Scientific Knowledge Graph Interoperability Framework (SKG-IF), are grouped together for the purpose of providing descriptive metadata compliant with the SKG-IF Data Model.")))
    onto.add((onto_iri, DC.date, 
              Literal(datetime.today().strftime('%Y-%m-%d'), datatype=XSD.date)))
    onto.add((onto_iri, VANN.preferredNamespacePrefix, Literal("skg-o")))
    onto.add((onto_iri, VANN.preferredNamespaceUri, 
              Literal(str(onto_iri), datatype=XSD.anyURI)))
    
    if version is not None:
        onto.add((onto_iri, OWL.versionIRI, onto_iri + version + "/"))
        onto.add((onto_iri, OWL.versionInfo, Literal(version)))
    
    for o_class in classes:
        iri = create_entity(o_class, OWL.Class, prefixes, onto, d_support)
        if iri is not None:
            domain_properties = get_domain_properties(o_class, d_support)

            if len(domain_properties):
                domain_strings = ["The properties that can be used with this class are:\n"]
                for property, target in domain_properties:
                    property_labels = d_support["term_mapping"][property]
                    for property_label in property_labels:
                        arity = d_support["arity"].get(property_label, None)
                        if arity is not None:
                            break

                    domain_strings.append("* " + property + " -" + ("[0..N]" if arity is None else "[" + arity + "]") + "-> " + target)
                
                onto.add((iri, DC.description, Literal("\n".join(domain_strings))))

    for o_objprop in object_properties:
        iri = create_entity(o_objprop, OWL.ObjectProperty, prefixes, onto, d_support)
        if iri is not None:
            create_domain_range(o_objprop, iri, onto, d_support, True)
    
    for o_dataprop in data_properties:
        iri = create_entity(o_dataprop, OWL.DatatypeProperty, prefixes, onto, d_support)
        if iri is not None:
            create_domain_range(o_dataprop, iri, onto, d_support, False)
    
    for o_ind in individuals:
        create_entity(o_ind, OWL.NamedIndividual, prefixes, onto, d_support)
    
    return onto


def store(ontology, dest_dir, file_name, format):
    if not exists(dest_dir):
        makedirs(dest_dir)
    dest_file = dest_dir + sep + file_name
    ontology.serialize(dest_file, format=format)


# Main
if __name__ == "__main__":
    arg_parser = ArgumentParser("create_ontology.py - Create the ontology defined in the graphs of the SKG-IF Data Model, also reusing the documentation of the SKG Interoperability Framework")
    arg_parser.add_argument("-g", "--graphs", dest="graphs_dir", required=True,
                            help="The directory that includes the .graphml files defining the SKG-IF Data Model.")
    arg_parser.add_argument("-d", "--docs", dest="docs_path", required=True,
                            help="The directory that includes the SKG-IF documentation to use to fill in the annotations of the ontology.")
    arg_parser.add_argument("-o", "--output", dest="output_path", required=True,
                            help="The path where to store the ontology to create.")
    arg_parser.add_argument("-v", "--version", dest="version_number",
                            help="The version (in semantic versioning format, i.e. X.Y.Z) of the ontology to be created.")
    args = arg_parser.parse_args()

    # Set logger
    log = logging.getLogger("GeRFo logger")
    log_h = logging.StreamHandler()
    log_f = logging.Formatter('%(levelname)s - %(message)s')
    log_h.setFormatter(log_f)
    log.addHandler(log_h)
    log.setLevel(logging.INFO)

    d = {
        "term_mapping": defaultdict(set),
        "entity_id": defaultdict(set),
        "id_entity": defaultdict(set),
        "domain_range": defaultdict(dict),
        "definitions": defaultdict(str),
        "arity": defaultdict(str)
    } 

    log.info("Extracting the ontological entities from the .graphml files of the data mode.")

    class_terms = set()
    property_terms = set()
    individual_terms = set()

    for c in glob(args.graphs_dir + sep + "*.graphml"):
        log.info("Processing file '%s'." % c)
        file_name = sub(".*(skg-if-.+).graphml$", "\\1", c)
        
        with open(c, mode="r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "xml")

        log.info("Extracting the nodes of the graph '%s' to identify potential OWL classes and individuals." % file_name)
        node_terms = gather_entities_and_labels(soup, False, d, file_name)
        for term in node_terms:
            if search("[^:]:[a-z]", term) is None:
                class_terms.add(term)
            else:
                individual_terms.add(term)
        
        log.info("Extracting the edges of the graph '%s' to identify potential OWL properties." % file_name)
        edge_terms = gather_entities_and_labels(soup, True, d, file_name)
        for term in edge_terms:
            property_terms.add(term)

    log.info("Identifying all OWL datatypes defined in all the .graphml files.")
    datatype_set = set()
    extract_datatypes(individual_terms, {"xsd"}, datatype_set)
    extract_datatypes(class_terms, {"rdfs"}, datatype_set)

    log.info("Identifying OWL object properties and data properties from the properties extracted from all the .graphml files.")
    object_property_terms = set()
    data_property_terms = set()
    for property in property_terms:
        entity_ranges = get_domain_range_entity_names(property, False, d)
        for entity_range in entity_ranges:
            if entity_range in datatype_set:
                data_property_terms.add(property)
            else:
                object_property_terms.add(property)

    log.info("Extracting annotations for all the OWL entities extracted from the documents included in the SKG-IF documentation.")
    for c in glob(args.docs_path + sep + "*.md"):
        log.info("Processing file '%s'." % c)
        file_name = sub(".*/(.+).md$", "\\1", c)
        
        with open(c, mode="r", encoding="utf-8") as f:
            file_string = f.read()

            log.info("Extracting the entity definitions from the document '%s'." % file_name)
            associate_definitions([
                ("\n# (.+)[\\n\\s]+(.+)", None),
                ("\n### (.+)[\\n\\s]+(.+)", "^[^:]+: (.+)"),
                ("\n\s*- `(.+)` \*[^\*]+\* [^:]+: (.+)", "^[^:]+: (.+)"),
                ("\n\s*- `(.+)`: (.+)", "^[^:]+: (.+)")
            ], file_string, d)

            log.info("Extracting the arity of all the OWL object and data properties as defined in the document '%s'." % file_name)
            arity_re = "(\s*- `([^`]+)` |### `([^`]+)`\s*\n+)\*([^\*]+)\* \((mandatory|recommended|optional)\)"
            arity_def = findall(arity_re, file_string)
            for _, e_name_v1, e_name_v2, p_type, arity in arity_def:
                entity = e_name_v1 if e_name_v1 != "" else e_name_v2

                if arity == "mandatory":
                    l_const = "1"
                else:
                    l_const = "0"
                
                if p_type == "List":
                    r_const = "N"
                else:
                    r_const = "1"
                
                d["arity"][entity] = "1" if l_const == "1" and r_const == "1" else l_const + ".." + r_const

    version_number = None
    if args.version_number is not None:
        version_number = args.version_number.strip()

    log.info("Creating the ontology.")
    ontology = create_ontology(
        class_terms, object_property_terms, data_property_terms, individual_terms, 
        prefixes, d, version_number)
    
    if ontology is not None:
        log.info("Storing the ontology into the file system in different formats.")
        dir_name = dirname(args.output_path)
        file_name = splitext(basename(args.output_path))[0]
        for f in formats:
            store(ontology, dir_name + sep + "current", file_name + "." + formats[f], f)
            log.info("Ontology serialised %s format and stored in %s" % (f, dir_name + sep + "current"))
            if args.version_number is not None:
                store(ontology, dir_name + sep + version_number, 
                      file_name + "." + formats[f], f)
                log.info("Versioned ontology serialised %s format and stored in %s" % (f, dir_name + sep + version_number))