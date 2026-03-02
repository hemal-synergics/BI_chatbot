import json
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

# Connect to the local Elasticsearch container running on Docker Desktop
es = Elasticsearch(
    "http://localhost:9200",
    basic_auth=None,
    verify_certs=False,
    request_timeout=30
)

INDEX_NAME = "db_schemas"
DATA_INDEX = "sea_ticket_activity_log"

# Remote AWS credentials (used as db_credentials in seed data only)
HOST = "search-recommendation-engine-ic-new-ltjbsbfr3rs6duuoxwvbckkhee.ap-south-1.es.amazonaws.com"
PORT = 443
USER = "admin"
PASS = "CBD_EHc^jY%naw4y"


def setup_database():
    print("⏳ Connecting to Elasticsearch...")

    if not es.ping():
        print("❌ Could not connect to Elasticsearch.")
        print("   → Make sure Docker Desktop is running and the container is up.")
        print("   → Run: docker ps | grep elasticsearch")
        return

    print("✅ Connected to Elasticsearch on http://localhost:9200")

    # 1. Reset the index (drop if exists)
    if es.indices.exists(index=INDEX_NAME):
        print(f"🗑️  Deleting existing index '{INDEX_NAME}'...")
        es.indices.delete(index=INDEX_NAME)

    # 2. Create index with mapping
    mapping = {
        "mappings": {
            "properties": {
                "selected_topic": {"type": "keyword"},
                "databases": {
                    "type": "nested",
                    "properties": {
                        "db_name":        {"type": "keyword"},
                        "db_type":        {"type": "keyword"},
                        "db_description": {"type": "text"},
                        "db_schema":      {"type": "object", "enabled": False},
                        "db_credentials": {"type": "object", "enabled": False}
                    }
                }
            }
        }
    }

    print(f"🏗️  Creating index '{INDEX_NAME}'...")
    es.indices.create(index=INDEX_NAME, body=mapping)

    # 3. Seed data — single document for "call log" topic
    seed_data = [
        {
            "_index": INDEX_NAME,   # ✅ Fixed: was INDEX_NAMES (undefined)
            "_source": {
                "selected_topic": "call log",
                "databases": [
                    {
                        "db_name": DATA_INDEX,
                        "db_type": "elasticsearch",
                        "db_description": (
                            "Contains support activity logs, tracking client queries, "
                            "internal errors, ticket states, and time taken to resolve issues."
                        ),
                        "db_schema": {
                            "NAME":           "keyword",
                            "CLIENT":         "keyword",
                            "TYPE_OF_TASK":   "keyword",
                            "DISCUSSED_ON":   "keyword",
                            "TICKET_NO":      "keyword",
                            "REPETITIVE":     "keyword",
                            "STATUS":         "keyword",
                            "REMARKS":        "text",
                            "ENTRY_DATE":     "date",
                            "DISCUSSED_TIME": "keyword",
                            "SOLVING_TIME":   "keyword",
                            "TOTAL_TIME":     "keyword"
                        },
                        "db_credentials": {
                            "host":   HOST,
                            "port":   PORT,
                            "scheme": "https",
                            "user":   USER,
                            "pass":   PASS,
                            "index":  DATA_INDEX
                        }
                    }
                ]
            }
        }
    ]

    print("📥 Inserting seed data...")
    success, failed = bulk(es, seed_data)
    print(f"✅ Successfully inserted {success} document(s) into '{INDEX_NAME}'.")

    if failed:
        print(f"⚠️  {len(failed)} document(s) failed to insert: {failed}")

    # 4. Verify — fetch and print the inserted doc
    es.indices.refresh(index=INDEX_NAME)
    result = es.search(index=INDEX_NAME, body={"query": {"match_all": {}}})
    print(f"\n🔍 Verification — documents in '{INDEX_NAME}':")
    for hit in result["hits"]["hits"]:
        print(json.dumps(hit["_source"], indent=2))


if __name__ == "__main__":
    setup_database()