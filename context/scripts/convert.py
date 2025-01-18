from rdflib import Graph
import argparse

parser = argparse.ArgumentParser(
    prog='JSON-LD to Turtle converter',
    description='Useful to test if the RDF in JSON-LD complies with expectations')
parser.add_argument("input")
args = parser.parse_args()

g = Graph()
g.parse(args.input)
print(g.serialize(format="ttl"))