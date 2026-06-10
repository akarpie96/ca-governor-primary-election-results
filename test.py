import requests
import json

BASE_URL = "https://civicapi.org/api/v2"

queries = [
    "California Governor Open Primary",
    "CA Governor primary 2026",
    "California Governor open primary 2026",
]

for query in queries:
    url = f"{BASE_URL}/race/search"
    resp = requests.get(url, params={"query": query})
    print("\nQUERY:", query)
    print("URL:", resp.url)
    print("STATUS:", resp.status_code)
    print(json.dumps(resp.json(), indent=2))