from json import load, dump, dumps
from re import sub, findall
from datetime import timezone, datetime
import argparse


base = "https://w3id.org/oc/meta/"

# To complete with all OC Meta types
type_mapping = {
    "journal article": "http://purl.org/spar/fabio/JournalArticle",
    "book chapter": "http://purl.org/spar/fabio/BookChapter"
}

venue_mapping = {
    "journal article": "journal",
    "book chapter": "book"
}

def get_datetime(datetime_string):
    try:
        dt = datetime.strptime(item["pub_date"], "%Y-%m-%d")
    except ValueError:
        try:
            dt = datetime.strptime(item["pub_date"], "%Y-%m")
        except:
            dt = datetime.strptime(item["pub_date"], "%Y")
    
    return dt.replace(tzinfo=timezone.utc).isoformat()

def get_omid_url(string):
    return sub("^.*omid:([^ ]+).*$", base + "\\1", string)

def create_contributors(contributor_list, contributor_type):
    contributors = []
    agents = []
    
    contributor_rank = 0
    for contributor in contributor_list:
        if contributor != "":
            # new contributor
            contributor_rank += 1
            name, ids = findall("^(.+) \\[(.+)\\]$", contributor)[0]
            contributor_omid = get_omid_url(ids)

            contributor_object = {
                "by": contributor_omid,
                "role": contributor_type
            }

            if contributor_type != "publisher":
                contributor_object["rank"] = contributor_rank

            contributors.append(contributor_object)

            # related agent
            agent_object = {
                "local_identifier": contributor_omid,
            }

            # identifiers
            create_identifiers(ids, agent_object)

            # names
            if ", " in name:
                agent_object["entity_type"] = "person"

                fn, gn = name.split(", ")
                if gn:
                    agent_object["given_name"] = gn
                if fn:
                    agent_object["family_name"] = fn
            else:
                if contributor_type == "publisher":
                    agent_object["entity_type"] = "organisation"
                else:
                    agent_object["entity_type"] = "agent"
                
                if name:
                    agent_object["name"] = name
        
            agents.append(agent_object)

    return contributors, agents

def create_identifiers(identifiers, entity):
    for identifier in identifiers.split(" "):
        if "identifiers" not in entity:
            entity["identifiers"] = []
        
        scheme, value = identifier.split(":", 1)
        entity["identifiers"].append(
            {
                "scheme": scheme,
                "value": value
            }
        )

parser = argparse.ArgumentParser(
    prog='JSON OCDM API format to JSON-LD SKG-IF converter')
parser.add_argument("input")
parser.add_argument("output")
args = parser.parse_args()

with open(args.input, "r", encoding="utf-8") as f:
    oc_json = load(f)

    g = [] 

    result = {
        "@context": [ 
            "https://w3id.org/skg-if/context/skg-if.json",
            { 
                "@base": "https://w3id.org/skg-if/sandbox/oc/",
                "skg": "https://w3id.org/skg-if/sandbox/oc/"
            }
        ],
        "@graph": g
    }

    for item in oc_json:
        research_product = {
            "entity_type": "product"
        }
        g.append(research_product)
 
        # local identifier
        research_product["local_identifier"] = get_omid_url(item["id"])

        # identifiers
        create_identifiers(item["id"], research_product)

        # product type
        if item["type"] in ("data file", "dataset"):
            research_product["product_type"] = "research data"
        elif item["type"] in ("software"):
            research_product["product_type"] = "research software"
        else:
            research_product["product_type"] = "literature"

        # titles
        if "title" in item and item["title"] != "":
            research_product["titles"] = {
                "none": item["title"]
            }
        
        # contributions
        authors, author_agents = create_contributors(item["author"].split("; "), "author")
        editors, editor_agents = create_contributors(item["editor"].split("; "), "editor")
        publishers, publisher_agents = create_contributors(item["publisher"].split("; "), "publisher")
        
        research_product["contributions"] = authors + editors + publishers

        for agent in author_agents + editor_agents + publisher_agents:
            if agent not in g:
                g.append(agent)
        
        # manifestations
        manifestation = {
            "type": {
                "class": type_mapping[item["type"]],
                "labels": {
                    "en": item["type"]
                },
                "defined_in": "http://purl.org/spar/fabio"
            }
        }

        create_identifiers(item["id"], manifestation)
        
        if item["pub_date"] != "":
            print(get_datetime(item["pub_date"]))
            manifestation["dates"] = {
                "publication": get_datetime(item["pub_date"])
            }
        
        if item["volume"] != "" or item["page"] != "" or item["venue"] != "" or item["issue"] != "":
            manifestation["biblio"] = {}

            if item["issue"] != "":
                manifestation["biblio"]["issue"] = item["issue"]

            if item["volume"] != "":
                manifestation["biblio"]["volume"] = item["volume"]

            if item["page"] != "":
                sp, ep = item["page"].split("-")
                manifestation["biblio"]["pages"] = {
                    "first": sp,
                    "last": ep
                }

            if item["venue"] != "":
                name, ids = findall("^(.+) \\[(.+)\\]$", item["venue"])[0]
                venue_omid = get_omid_url(ids)

                manifestation["biblio"]["in"] = venue_omid

                venue_object = {
                    "local_identifier": venue_omid,
                    "entity_type": "venue",
                    "title": name,
                    "type": venue_mapping[item["type"]]
                }

                create_identifiers(ids, venue_object)

                if len(editors) and venue_mapping[item["type"]] in ("book"):
                    if "contributions" not in venue_object:
                        venue_object["contributions"] = []
                    venue_object["contributions"].extend(editors)
                
                if len(publishers):
                    if "contributions" not in venue_object:
                        venue_object["contributions"] = []
                    venue_object["contributions"].extend(publishers) 
                
                g.append(venue_object)

        research_product["manifestations"] = [ manifestation ]


with open(args.output, "w", encoding="utf-8") as f:
   dump(result, f, ensure_ascii=False, indent=4)

print(dumps(result, ensure_ascii=False, indent=4))
    